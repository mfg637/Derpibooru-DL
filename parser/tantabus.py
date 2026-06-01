from . import philomena, Parser
import database
import psycopg2
import logging
import typing

FILENAME_PREFIX = "ta"
ORIGIN = "tantabus"

logger = logging.getLogger(__name__)


def make_connection():
    try:
        return database.make_connection(
            database.DatabaseEnum.TANTABUS, none_if_error=True
        )
    except psycopg2.OperationalError:
        return None


class TantabusAIParser(philomena.Philomena):
    @staticmethod
    def get_domain_name_s():
        return "tantabus.ai"

    def get_filename_prefix(self):
        return FILENAME_PREFIX

    def get_origin_name(self):
        return ORIGIN

    def get_domain_name(self) -> str:
        return TantabusAIParser.get_domain_name_s()

    def custom_tag_processing(self) -> list[database.derpibooru.Tag] | None:
        if "__tags" in self.get_data()["image"]:
            return self.get_data()["image"]["__tags"]
        else:
            connection = make_connection()
            if connection is None:
                return None
            _id = int(self.getID())
            image_found = database.derpibooru.check_image_exists(
                connection, _id
            )
            if image_found:
                result = database.derpibooru.get_tags_of_image(connection, _id)
                connection.close()
                return result
            else:
                connection.close()
                return None

    def custom_data_loading(
        self, _id: int, request_type="images"
    ) -> dict[str, dict[str, typing.Any]] | None:
        db_local_instance = make_connection()
        data: dict | None = None
        if db_local_instance is not None:
            if request_type == "images":
                content_found = database.derpibooru.check_image_exists(
                    db_local_instance, _id
                )
                duplicate_of = database.derpibooru.check_duplicates(
                    db_local_instance, _id
                )
                if duplicate_of is not None:
                    logger.info("duplicate found")
                    data = self.parseJSON(duplicate_of)
                elif content_found:
                    logger.info("content_found")
                    data = database.derpibooru.simulate_image_api(
                        db_local_instance, _id, "tantabuscdn.net"
                    )
            db_local_instance.close()
        return data

    def get_auto_copyright_tags(self) -> set[str]:
        return {"my little pony"}

    def make_rate_limiter(self):
        return Parser.OneRequestPerSecondRateLimiter()

    def enable_html_parsing(self) -> bool:
        return False
