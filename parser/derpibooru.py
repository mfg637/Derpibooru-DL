import datetime
import logging
import time

import psycopg2

import database

from . import Parser, philomena


logger = logging.getLogger(__name__)

FILENAME_PREFIX = "db"
ORIGIN = "derpibooru"


def make_connection():
    try:
        return database.make_connection(database.DatabaseEnum.DERPIBOORU)
    except psycopg2.OperationalError:
        return None


class DerpibooruRateLimiter(Parser.RateLimiter):
    def rate_limit(self, request_type):
        if self.first_request_date is not None:
            current_timestamp = datetime.datetime.now()
            time_pass: datetime.timedelta = (
                current_timestamp - self.first_request_date
            )
            if self.request_timeout_seconds is None:
                pass
            elif time_pass.total_seconds() < self.request_timeout_seconds:
                if self.requests_count >= self.requests_limit:
                    waiting_time = (
                        self.request_timeout_seconds - time_pass.total_seconds()
                    )
                    logger.info(f"sleeping for {waiting_time} seconds")
                    time.sleep(waiting_time)
                    self.requests_count = 0
                    self.first_request_date = datetime.datetime.now()
                    self.request_timeout_seconds = None
            else:
                self.requests_count = 0
                self.first_request_date = datetime.datetime.now()
                self.request_timeout_seconds = None
        else:
            self.first_request_date = datetime.datetime.now()
        if request_type == "search":
            self.request_timeout_seconds = 10
            self.requests_limit = 10
        elif self.request_timeout_seconds is not None:
            self.request_timeout_seconds = max(self.request_timeout_seconds, 5)
            self.requests_limit = min(self.requests_limit, 30)
        else:
            self.request_timeout_seconds = 5
            self.requests_limit = 30


class DerpibooruParser(philomena.Philomena):
    def get_origin_name(self):
        return ORIGIN

    def get_domain_name(self) -> str:
        return DerpibooruParser.get_domain_name_s()

    @staticmethod
    def get_domain_name_s():
        return "derpibooru.org"

    def get_filename_prefix(self):
        return FILENAME_PREFIX

    def get_auto_copyright_tags(self) -> set[str]:
        return {"my little pony"}

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

    def make_rate_limiter(self) -> DerpibooruRateLimiter:
        return DerpibooruRateLimiter()

    def custom_data_loading(self, _id: int, request_type="images"):
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
                        db_local_instance, _id
                    )
            db_local_instance.close()
        return data
