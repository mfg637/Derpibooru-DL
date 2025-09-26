import abc
import json
import logging
import pathlib
import sys
import enum
import typing
import database
from html.parser import HTMLParser

from database import origin_tag
import parser
from parser import derpibooru
from .Parser import Parser

import requests

import config

logger = logging.getLogger(__name__)


class Philomena(Parser):
    def parseHTML(self, image_id) -> dict[str, str]:
        """
        Parse tags by HTML page.
        :param image_id:
        :return: {"tag name 1": "tag category 1", …}
        """
        global tags_parsed_data
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

    def tags_processing(self) -> dict[str, list[str]]:
        connection = database.make_connection(database.DatabaseEnum.APP_PROD)
        custom_processing_data = self.custom_tag_processing()
        known_tags: list[database.origin_tag.OriginTag] = []
        origin = database.origin_tag.OriginNameType(self.get_origin_name())
        if custom_processing_data is None:
            unknown_tags: list[str] = []
            tag_names = self.getTagNamesList()
            for tag_info in tag_names:
                tag_data = database.origin_tag.get_by_tag_name(
                    connection, origin, tag_info
                )
                if tag_data is None:
                    unknown_tags.append(tag_info)
                else:
                    known_tags.append(tag_data)
            if len(unknown_tags):
                derpibooru_connection = None
                if origin is database.origin_tag.OriginNameType.DERPIBOORU:
                    derpibooru_connection = database.make_connection(
                        database.DatabaseEnum.DERPIBOORU
                    )
                tag_name_to_slug = self.parseHTML(self.getID())
                for tag_info in unknown_tags:
                    tag_data = None
                    if derpibooru_connection is not None:
                        tag_data = database.derpibooru.simulate_tag_api(
                            derpibooru_connection, tag_info
                        )
                    if tag_data is None:
                        tag_data = self.parseJSON(
                            url=tag_name_to_slug[tag_info], _type="tags"
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
        result: dict[str, list[str]] = dict()
        for tag_info in known_tags:
            if str(tag_info.category) not in result:
                result[str(tag_info.category)] = []
            result[str(tag_info.category)].append(tag_info.tag_name)
        connection.close()
        return result
