import abc
import re
import os
import json
import logging
import pathlib
import sys
import database
import time
import urllib.parse
from html.parser import HTMLParser

from database import origin_tag
from .Parser import Parser, FileTypes

import requests
import config


logger = logging.getLogger(__name__)


class Philomena(Parser):
    def __init__(self, url, parsed_data: dict | None = None):
        super().__init__(url, parsed_data)
        self.rate_limiter = self.make_rate_limiter()

    def parseHTML(self, image_id) -> dict[str, str]:
        """
        Parse tags by HTML page.
        :param image_id:
        :return: {"tag name 1": "tag category 1", …}
        """
        # philomena's API didn't provide method to get tag slug
        # image route also didn't contain that data
        # you either need a database dump or extract info from html
        tags_parsed_data = dict()
        request_url = "https://{}/{}/{}".format(
            self.get_domain_name(),
            self.parsehtml_get_image_route_name(),
            image_id,
        )
        print("parseHTML", request_url, file=sys.stderr)
        try:
            request_data = requests.get(request_url)
        except Exception as e:
            print(e, file=sys.stderr)
            return dict()
        raw_html = request_data.text

        class TagsParser(HTMLParser):
            def error(self, message):
                raise Exception(message)

            def handle_starttag(self, tag, attrs):
                if tag in {"div", "span"}:
                    attributes = dict(attrs)
                    if (
                        "data-tag-name" in attributes.keys()
                        and "data-tag-slug" in attributes.keys()
                    ):
                        tags_parsed_data[attributes["data-tag-name"]] = (
                            attributes["data-tag-slug"]
                        )

        _parser = TagsParser()
        _parser.feed(raw_html)
        return tags_parsed_data

    @abc.abstractmethod
    def custom_tag_processing(self) -> list[database.derpibooru.Tag] | None:
        pass

    def translate_origin_tag_to_tags(
        self, tag_data: dict | database.derpibooru.Tag
    ):
        def translate_tag(
            name: str, category: str | None, auto_tags: set[str]
        ) -> tuple[str, database.tag.TagCategory]:
            categories = database.tag.TagCategory
            if category == "character":
                auto_tags = self.get_auto_copyright_tags()
                if "my little pony" in auto_tags:
                    return f"{name} (mlp)", categories.CHARACTER
                else:
                    return name, categories.CHARACTER
            elif category == "content-fanmade":
                if name.startswith("comic:"):
                    return name.removeprefix("comic:"), categories.COMIC
                else:
                    return name, categories.SET
            elif category == "content-official":
                return name, categories.COPYRIGHT
            elif category == "error":
                return name, categories.ERROR
            elif category == "oc":
                return name, categories.CHARACTER
            elif category == "origin":
                if name.startswith("artist:"):
                    return name.removeprefix("artist:"), categories.ARTIST
                elif name.startswith("prompter:"):
                    return name.removeprefix("prompter:"), categories.PROMPTER
                else:
                    return name, categories.ARTIST
            elif category == "rating":
                return name, categories.RATING
            elif category == "species":
                return name, categories.SPECIES
            elif category == "spoiler":
                return name, categories.LORE
            else:
                return name, categories.CONTENT

        if isinstance(tag_data, database.derpibooru.Tag):
            return translate_tag(
                tag_data.name, tag_data.category, self.get_auto_copyright_tags()
            )
        elif type(tag_data) is dict:
            return translate_tag(
                tag_data["tag"]["name"],
                tag_data["tag"]["category"],
                self.get_auto_copyright_tags(),
            )
        else:
            raise TypeError(f"Unexpected type: {type(tag_data)}")

    def tags_processing(self) -> dict[str, set[str]]:
        connection = database.make_connection(database.DatabaseEnum.APP_PROD)
        custom_processing_data = self.custom_tag_processing()
        known_tags: list[database.origin_tag.OriginTag] = []
        origin = database.origin_tag.OriginNameType(self.get_origin_name())
        if custom_processing_data is None:
            unknown_tags: list[str] = []
            tag_names = self.getTagNamesList()
            for origin_tag_info in tag_names:
                tag_data = database.origin_tag.get_by_tag_name(
                    connection, origin, origin_tag_info
                )
                if tag_data is None:
                    unknown_tags.append(origin_tag_info)
                else:
                    known_tags.append(tag_data)
            if len(unknown_tags):
                derpibooru_connection = None
                if origin is database.origin_tag.OriginNameType.DERPIBOORU:
                    derpibooru_connection = database.make_connection(
                        database.DatabaseEnum.DERPIBOORU
                    )
                tag_name_to_slug = self.parseHTML(self.getID())
                for origin_tag_info in unknown_tags:
                    tag_data = None
                    if derpibooru_connection is not None:
                        tag_data = database.derpibooru.simulate_tag_api(
                            derpibooru_connection, origin_tag_info
                        )
                    if tag_data is None:
                        tag_data = self.parseJSON(
                            url=tag_name_to_slug[origin_tag_info], _type="tags"
                        )
                    if tag_data is None:
                        raise Exception("tag API error: no tag info")
                    ddl_tag_name, ddl_tag_category = (
                        self.translate_origin_tag_to_tags(tag_data)
                    )
                    tag_id = database.tag.get_or_create_tag_id(
                        connection, ddl_tag_name, ddl_tag_category
                    )
                    if tag_id is None:
                        raise Exception("Failed to add a new tag")
                    origin_tag_builder = database.origin_tag.OriginTagBuilder()
                    origin_tag_builder.tag_id = tag_id
                    origin_tag_builder.origin_name = origin
                    origin_tag_builder.tag_name = tag_data["tag"]["name"]
                    origin_tag_builder.tag_slug = tag_data["tag"]["slug"]
                    origin_tag_builder.description = tag_data["tag"][
                        "description"
                    ]
                    origin_tag_builder.short_description = tag_data["tag"][
                        "short_description"
                    ]
                    origin_tag_builder.category = tag_data["tag"]["category"]
                    origin_tag_data = origin_tag_builder.build()
                    origin_tag.add_if_not_exists(connection, origin_tag_data)
                    known_tags.append(origin_tag_data)
                if derpibooru_connection is not None:
                    derpibooru_connection.close()
        else:
            for derpibooru_tag in custom_processing_data:
                existing_origin_tag = database.origin_tag.get_by_tag_name(
                    connection, origin, derpibooru_tag.name
                )
                if existing_origin_tag is None:
                    ddl_tag_name, ddl_tag_category = (
                        self.translate_origin_tag_to_tags(derpibooru_tag)
                    )
                    tag_id = database.tag.get_or_create_tag_id(
                        connection, ddl_tag_name, ddl_tag_category
                    )
                    if tag_id is None:
                        raise Exception("Failed to add a new tag")
                    origin_tag_builder = database.origin_tag.OriginTagBuilder()
                    origin_tag_builder.tag_id = tag_id
                    origin_tag_builder.origin_name = origin
                    origin_tag_builder.tag_name = derpibooru_tag.name
                    origin_tag_builder.tag_slug = derpibooru_tag.slug
                    origin_tag_builder.description = derpibooru_tag.description
                    origin_tag_builder.short_description = (
                        derpibooru_tag.short_description
                    )
                    origin_tag_builder.category = derpibooru_tag.category
                    origin_tag_data = origin_tag_builder.build()
                    origin_tag.add_if_not_exists(connection, origin_tag_data)
                    known_tags.append(origin_tag_data)
                else:
                    known_tags.append(existing_origin_tag)
        result: dict[str, set[str]] = dict()
        for origin_tag_info in known_tags:
            tag_info = database.tag.get_tag_by_id(
                connection, origin_tag_info.tag_id
            )
            if tag_info is None:
                raise Exception("Fail to get tag info")
            if str(tag_info.category) not in result:
                result[str(tag_info.category)] = set()
            result[str(tag_info.category)].add(tag_info.name)
        auto_tags = list(self.get_auto_copyright_tags())
        copyright_category_name = str(database.tag.TagCategory.COPYRIGHT)
        if len(auto_tags):
            if copyright_category_name not in result:
                result[copyright_category_name] = set()
        for tag_name in auto_tags:
            result[copyright_category_name].add(tag_name)
        connection.close()
        return result

    def get_raw_content_data(self):
        return self.get_data()["image"]

    def get_content_id(self) -> int:
        result = int(self.get_raw_content_data()["id"])
        if type(result) is int:
            return result
        else:
            raise ValueError("Unable to convert content ID to integer")

    @abc.abstractmethod
    def custom_data_loading(
        self, _id: int, request_type="images"
    ) -> dict | None:
        pass

    def parseJSON(self, url=None, _type="images", trial_count=2) -> dict | None:
        _id = None
        if url is not None:
            _id = url
        else:
            _id = self.get_id_by_url(self._url)
        if _id is None:
            raise TypeError(f"ID: {_id} is still None")
        data: dict | None = None
        if type(_id) is int:
            data = self.custom_data_loading(_id, _type)
        else:
            logger.warning("url(id) is not int. Can't use custom data loading")
        if data is None:
            request_url = "https://{}/api/v1/json/{}/{}".format(
                self.get_domain_name_s(), _type, urllib.parse.quote(str(_id))
            )
            logger.debug("url: {}".format(url))
            logger.info("parseJSON: {}".format(request_url))
            self.rate_limiter.rate_limit(_type)
            try:
                request_data = requests.get(request_url)
            except Exception as e:
                print(e)
                return
            finally:
                self.rate_limiter.increment_requests_count()
            data = None
            if request_data.status_code == 404:
                raise IndexError('not found "{}"'.format(url))
            try:
                data = request_data.json()
            except json.JSONDecodeError as e:
                sleep_time_seconds = 5
                sleep_time_text = "5 seconds"
                if request_data.status_code == 500 or trial_count <= 1:
                    sleep_time_seconds = 16 * 60
                    sleep_time_text = "16 minutes"
                if trial_count > 0:
                    logger.warning(
                        (
                            "JSON decode error. "
                            f"HTTP status code:{request_data.status_code} "
                            f"Raw data: \n{request_data.text}"
                        )
                    )
                    print(f"try again after {sleep_time_text}")
                    time.sleep(sleep_time_seconds)
                    return self.parseJSON(url, _type, trial_count - 1)
                else:
                    logger.error(
                        (
                            "JSON decode error. "
                            f"HTTP status code:{request_data.status_code} "
                            f"Raw data: \n{request_data.text}"
                        )
                    )
                    raise e
            while (
                data is not None
                and _type == "images"
                and "duplicate_of" in data["image"]
                and data["image"]["duplicate_of"] is not None
            ):
                data = self.parseJSON(str(data["image"]["duplicate_of"]))
        if (
            data is not None
            and _type == "images"
            and "tags" not in data["image"]
        ):
            data["image"]["tags"] = []
        if _type == "images":
            self._parsed_data = data
        return data

    def parsehtml_get_image_route_name(self) -> str:
        return "images"

    def getTagNamesList(self) -> list[str]:
        return self.get_data()["image"]["tags"]

    def getID(self) -> str:
        try:
            return str(self.get_data()["image"]["id"])
        except KeyError as e:
            print(self.get_data())
            raise e

    def dataValidator(self, data):
        if "image" not in data:
            raise KeyError("data has no 'image'")
        data = data["image"]
        if "representations" not in data:
            raise KeyError("data has no 'representations'")
        if "full" not in data["representations"]:
            raise KeyError("not found full representation")
        if type(data["representations"]["full"]) is not str:
            raise TypeError(
                "data['representations']['full'] is not str: "
                + data["representations"]["full"].__class__.__name__
            )
        if type(os.path.splitext(data["representations"]["full"])) is not tuple:
            raise TypeError(
                "os.path.splitext(data['representations']['full']) is not tuple: "
                + os.path.splitext(
                    data["representations"]["full"]
                ).__class__.__name__
            )
        if (
            type(os.path.splitext(data["representations"]["full"])[0])
            is not str
        ):
            raise TypeError(
                "os.path.splitext(data['representations']['full'])[0] is not str: "
                + os.path.splitext(data["representations"]["full"])[
                    0
                ].__class__.__name__
            )
        if "format" not in data:
            raise KeyError("data has no format property")
        if type(data["format"]) is not str:
            raise TypeError(
                'data["format"] is not str: '
                + data["format"].__class__.__name__
            )
        if "large" not in data["representations"]:
            raise KeyError("not found large representation")

    def check_is_takedowned(self, data):
        return (
            "deletion_reason" in data["image"]
            and data["image"]["deletion_reason"] is not None
        )

    def get_takedowned_content_info(self, data):
        return self.file_deleted_handing(
            self.get_filename_prefix(), data["image"]["id"]
        )

    def get_content_source_url(self, data):
        return (
            os.path.splitext(data["image"]["representations"]["full"])[0]
            + "."
            + data["image"]["format"].lower()
        )

    def get_output_filename(
        self, data, output_directory: pathlib.Path
    ) -> tuple[str, pathlib.Path]:
        data = data["image"]
        name = ""
        if (
            "name" in data
            and data["name"] is not None
            and config.source_name_as_file_name
        ):
            name = "{}{} {}".format(
                self.get_filename_prefix(),
                data["id"],
                re.sub(
                    r'[/\[\]:;|=*".?]', "", os.path.splitext(data["name"])[0]
                )[: config.max_name_length],
            )
        else:
            name = "{}{}".format(self.get_filename_prefix(), data["id"])
        name = Parser.sanitise_filename(name)
        return name, output_directory.joinpath(
            "{}.{}".format(name, data["format"].lower())
        )

    def get_image_metadata(self, data):
        return {
            "title": data["image"]["name"],
            "origin": self.get_origin_name(),
            "id": data["image"]["id"],
        }

    def get_image_format(self, data):
        return data["image"]["format"]

    def get_big_thumbnail_url(self, data):
        return data["image"]["representations"]["large"]

    def identify_filetype(self) -> FileTypes:
        filetype = Parser.identify_by_mimetype(
            self.get_data()["image"]["mime_type"]
        )
        if (
            filetype == FileTypes.IMAGE
            and "animated" in self.get_data()["image"]["tags"]
        ):
            filetype = FileTypes.ANIMATION
        return filetype
