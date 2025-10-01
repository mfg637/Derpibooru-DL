import database
from . import philomena, Parser

FILENAME_PREFIX = "pb"
ORIGIN = "ponybooru"


class PonybooruParser(philomena.Philomena):
    @staticmethod
    def get_domain_name_s():
        return "ponybooru.org"

    def get_filename_prefix(self):
        return FILENAME_PREFIX

    def get_origin_name(self):
        return ORIGIN

    def get_domain_name(self) -> str:
        return PonybooruParser.get_domain_name_s()

    def custom_tag_processing(self):
        return None

    def custom_data_loading(
        self, _id: int, request_type="images"
    ) -> dict | None:
        return None

    def get_auto_copyright_tags(self) -> set[str]:
        return {"my little pony"}

    def make_rate_limiter(self):
        return Parser.OneRequestPerSecondRateLimiter()

    def tags_processing(self) -> dict[str, set[str]]:
        connection = database.make_connection(database.DatabaseEnum.APP_PROD)
        known_tags: list[database.origin_tag.OriginTag] = []
        origin = database.origin_tag.OriginNameType.PONYBOORU
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
            for origin_tag_info in unknown_tags:
                tag_data = None
                if tag_data is None:
                    tag_data = self.parseJSON(
                        url="tags", _type="search", q=origin_tag_info
                    )
                if tag_data is None:
                    raise Exception("tag API error: no tag info")
                tag_data_adapter = {"tag": tag_data["tags"][0]}
                ddl_tag_name, ddl_tag_category = (
                    self.translate_origin_tag_to_tags(tag_data_adapter)
                )
                tag_id = database.tag.get_or_create_tag_id(
                    connection, ddl_tag_name, ddl_tag_category
                )
                if tag_id is None:
                    raise Exception("Failed to add a new tag")
                origin_tag_builder = database.origin_tag.OriginTagBuilder()
                origin_tag_builder.tag_id = tag_id
                origin_tag_builder.origin_name = origin
                origin_tag_builder.tag_name = tag_data["tags"][0]["name"]
                origin_tag_builder.tag_slug = tag_data["tags"][0]["slug"]
                origin_tag_builder.description = tag_data["tags"][0][
                    "description"
                ]
                origin_tag_builder.short_description = tag_data["tags"][0][
                    "short_description"
                ]
                origin_tag_builder.category = tag_data["tags"][0]["category"]
                origin_tag_data = origin_tag_builder.build()
                database.origin_tag.add_if_not_exists(
                    connection, origin_tag_data
                )
                known_tags.append(origin_tag_data)
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

    def parseHTML(self, image_id) -> dict[str, str]:
        raise Exception(
            "ParseHTML is forbidden on Ponybooru (returns 403 status code)"
        )
