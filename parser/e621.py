import json
import logging
import pathlib
import time
import typing
import urllib
import base64
import urllib.parse

import database
import file_format
from .Parser import FileTypes

import requests

import config
from . import Parser

logger = logging.getLogger(__name__)

FILENAME_PREFIX = "ef"
ORIGIN = "e621"


class E621Parser(Parser.Parser):
    def __init__(self, url, parsed_data: dict | None = None):
        super().__init__(url, parsed_data)
        self.rate_limiter = Parser.OneRequestPerSecondRateLimiter()

    def identify_filetype(self) -> FileTypes:
        FILE_EXTENSION_ASSOCIATION: typing.Final[dict[str, FileTypes]] = {
            "jpg": FileTypes.IMAGE,
            "jpeg": FileTypes.IMAGE,
            "png": FileTypes.IMAGE,
            "gif": FileTypes.ANIMATION,
            "webm": FileTypes.VIDEO,
            "webp": FileTypes.VIDEO,
        }
        filetype = FILE_EXTENSION_ASSOCIATION[
            self.get_data()["post"]["file"]["ext"].lower()
        ]
        if (
            filetype == FileTypes.IMAGE
            and "animated" in self.get_data()["post"]["tags"]["meta"]
        ):
            filetype = FileTypes.ANIMATION
        return filetype

    def parsehtml_get_image_route_name(self) -> str:
        raise NotImplementedError()

    def get_domain_name(self) -> str:
        return E621Parser.get_domain_name_s()

    @staticmethod
    def get_domain_name_s():
        return "e621.net"

    def getID(self) -> str:
        return str(self.get_data()["post"]["id"])

    def dataValidator(self, data):
        pass

    def get_filename_prefix(self):
        return FILENAME_PREFIX

    def get_origin_name(self):
        return ORIGIN

    def parseJSON(self, url=None, _type="posts", trial_count=2):
        headers = {
            "User-Agent": "Derpibooru-DL (by mfg637) (https://github.com/mfg637/Derpibooru-DL)"
        }
        if config.e621_login is not None and config.e621_API_KEY is not None:
            auth_string = f"{config.e621_login}:{config.e621_API_KEY}"
            auth_base64 = base64.b64encode(auth_string.encode("utf-8")).decode(
                "utf-8"
            )
            headers["Authorization"] = f"Basic {auth_base64}"

        id = None
        if url is not None:
            id = url
        else:
            id = self.get_id_by_url(self._url)
        request_url = "https://{}/{}/{}.json".format(
            self.get_domain_name_s(), _type, urllib.parse.quote(str(id))
        )
        self.rate_limiter.rate_limit(_type)
        logger.info("parseJSON: {}".format(request_url))
        request_data = None
        try:
            request_data = requests.get(request_url, headers=headers)
        except json.JSONDecodeError as e:
            if trial_count > 0:
                logger.warning(
                    "JSON decode error. HTTP status code:{} Raw data: \n{}".format(
                        request_data.status_code, request_data.text
                    )
                )
                print("try again after 10 minutes")
                time.sleep(600)
                return self.parseJSON(url, _type, trial_count - 1)
            else:
                logger.error(
                    "JSON decode error. HTTP status code:{} Raw data: \n{}".format(
                        request_data.status_code, request_data.text
                    )
                )
                raise e
        finally:
            self.rate_limiter.increment_requests_count()
        data = None
        if request_data.status_code == 404:
            raise IndexError('not founded "{}"'.format(url))
        logger.debug("STATUS CODE: {}".format(request_data.status_code))
        try:
            data = request_data.json()
        except json.JSONDecodeError as e:
            logger.error(
                "JSON decode error. HTTP status code:{} Raw data: {}".format(
                    request_data.status_code, request_data.text
                )
            )
            raise e
        self._parsed_data = data
        return data

    def check_is_takedowned(self, data):
        # takedowned content example: https://e621.net/posts/1744852.json
        return data["post"]["flags"]["deleted"]

    def get_takedowned_content_info(self, data):
        logging.exception("deleted image ef{}".format(data["post"]["id"]))
        if config.deleted_image_list_file_path is not None:
            deleted_list_f = pathlib.Path(
                config.deleted_image_list_file_path
            ).open("a")
            general_tags_category = (
                "general",
                "species",
                "meta",
                "invalid",
                "lore",
            )
            for category in general_tags_category:
                deleted_list_f.write(
                    "{}{}: {}\n".format(
                        "ef",
                        data["post"]["id"],
                        ", ".join(
                            [str(key) for key in data["post"]["tags"][category]]
                        ),
                    )
                )
            deleted_list_f.write(
                "{}{}: character:{}\n".format(
                    "ef",
                    data["post"]["id"],
                    ", ".join(
                        [str(key) for key in data["post"]["tags"]["character"]]
                    ),
                )
            )
            deleted_list_f.write(
                "{}{}: copyright:{}\n".format(
                    "ef",
                    data["post"]["id"],
                    ", ".join(
                        [str(key) for key in data["post"]["tags"]["copyright"]]
                    ),
                )
            )
            deleted_list_f.close()
        return 0, 0, 0, 0

    def get_content_source_url(self, data):
        representation_url_string = data["post"]["file"]["url"]
        if representation_url_string is None:
            raise Exception("Access denied by e621")
        representation_url_object = urllib.parse.urlparse(
            representation_url_string
        )
        url_path_component = pathlib.PurePosixPath(
            representation_url_object.path
        )
        url_path_with_new_suffix = url_path_component.with_suffix(
            ".{}".format(data["post"]["file"]["ext"].lower())
        )
        new_representation_url = representation_url_object._replace(
            path=str(url_path_with_new_suffix)
        )
        return urllib.parse.urlunparse(new_representation_url)

    def get_output_filename(
        self, data, output_directory: pathlib.Path
    ) -> tuple[str, pathlib.Path]:
        data = data["post"]
        name = ""
        print(data["id"], data["file"]["url"], data["file"]["ext"])
        if data["file"]["url"] is None or data["file"]["ext"] is None:
            print(data)
        name = "{}{}".format(FILENAME_PREFIX, data["id"])
        return name, output_directory.joinpath(
            "{}.{}".format(name, data["file"]["ext"].lower())
        )

    def get_image_metadata(self, data):
        return {
            "title": None,
            "origin": self.get_origin_name(),
            "id": data["post"]["id"],
        }

    def get_image_format(self, data):
        return data["post"]["file"]["ext"]

    def get_big_thumbnail_url(self, data):
        return data["post"]["sample"]["url"]

    def get_raw_content_data(self) -> dict:
        return self.get_data()["post"]

    def tags_processing(self) -> dict[str, set[str]]:
        connection = database.make_connection(database.DatabaseEnum.APP_PROD)
        if connection is None:
            raise Exception("Failed to connect to database")
        origin_tags_dict = self.get_raw_content_data()["tags"]
        categories = database.tag.TagCategory
        origin = database.origin_tag.OriginNameType.E621
        category_translation_table: dict[str, database.tag.TagCategory] = {
            "general": categories.CONTENT,
            "artist": categories.ARTIST,
            "copyright": categories.COPYRIGHT,
            "character": categories.CHARACTER,
            "species": categories.SPECIES,
            "invalid": categories.ERROR,
            "meta": categories.META,
            "lore": categories.LORE,
            "contributor": categories.CREATOR,
        }
        result: dict[str, set[str]] = dict()
        for origin_category in origin_tags_dict:
            for origin_tag_name in origin_tags_dict[origin_category]:
                origin_tag = database.origin_tag.get_by_tag_name(
                    connection, origin, origin_tag_name
                )
                if origin_tag is None:
                    tag_id = database.tag.get_or_create_tag_id(
                        connection,
                        origin_tag_name.replace("_", " "),
                        category_translation_table[origin_category],
                    )
                    if tag_id is None:
                        raise Exception("Failed to get tag id")
                    origin_tag_builder = database.origin_tag.OriginTagBuilder()
                    origin_tag_builder.tag_id = tag_id
                    origin_tag_builder.tag_name = origin_tag_name
                    origin_tag_builder.category = origin_category
                    origin_tag_builder.origin_name = origin
                    origin_tag_data = origin_tag_builder.build()
                    database.origin_tag.add_if_not_exists(
                        connection, origin_tag_data
                    )
                    tag_info = database.tag.get_tag_by_id(connection, tag_id)
                    if tag_info is None:
                        raise Exception("Failed to get tag info")
                    if str(tag_info.category) not in result:
                        result[str(tag_info.category)] = set()
                    result[str(tag_info.category)].add(tag_info.name)
                else:
                    tag_info = database.tag.get_tag_by_id(
                        connection, origin_tag.tag_id
                    )
                    if tag_info is None:
                        raise Exception(
                            (
                                "Database anomaly found on tag id = "
                                f"{origin_tag.tag_id}"
                            )
                        )
                    if str(tag_info.category) not in result:
                        result[str(tag_info.category)] = set()
                    result[str(tag_info.category)].add(tag_info.name)
        connection.close()
        RATING_NAME = {"s": "safe", "q": "questionable", "e": "explicit"}
        result[categories.RATING] = {
            RATING_NAME[self.get_raw_content_data()["rating"]],
        }
        return result

    def get_content_id(self) -> int:
        return self.get_raw_content_data()["id"]

    def getTagNamesList(self) -> list[str]:
        tags = self.get_raw_content_data()["tags"]
        result = []
        for category in tags:
            result.append(tags[category])
        return result

    def parseHTML(self, image_id) -> dict[str, str]:
        raise NotImplementedError("Not supported by E621")

    def make_rate_limiter(self) -> Parser.RateLimiter:
        return Parser.OneRequestPerSecondRateLimiter()

    def get_mime_type(self) -> str:
        ext = self.get_raw_content_data()["file"]["ext"]
        return file_format.MIME_BY_EXTENSION[f".{ext}"]
