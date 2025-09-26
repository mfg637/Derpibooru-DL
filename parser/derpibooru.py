import datetime
import json
import logging
import os
import pathlib
import re
import time
import urllib.parse

import psycopg2

import database
from .Parser import FileTypes

import requests

from . import Parser, philomena


logger = logging.getLogger(__name__)

FILENAME_PREFIX = "db"
ORIGIN = "derpibooru"


def make_connection():
    try:
        return database.make_connection(database.DatabaseEnum.DERPIBOORU)
    except psycopg2.OperationalError:
        return None


first_request_date = None
request_timeout_seconds = None
requests_count = 0
requests_limit = 0


class DerpibooruParser(philomena.Philomena):
    def identify_filetype(self) -> FileTypes:
        filetype = Parser.Parser.identify_by_mimetype(
            self.get_data()["image"]["mime_type"]
        )
        if (
            filetype == FileTypes.IMAGE
            and "animated" in self.get_data()["image"]["tags"]
        ):
            filetype = FileTypes.ANIMATION
        return filetype

    def get_origin_name(self):
        return ORIGIN

    def getID(self) -> str:
        try:
            return str(self.get_data()["image"]["id"])
        except KeyError as e:
            print(self.get_data())
            raise e

    def getTagNamesList(self) -> list[str]:
        return self.get_data()["image"]["tags"]

    def parsehtml_get_image_route_name(self) -> str:
        return "images"

    def get_domain_name(self) -> str:
        return DerpibooruParser.get_domain_name_s()

    @staticmethod
    def get_domain_name_s():
        return "derpibooru.org"

    def get_filename_prefix(self):
        return FILENAME_PREFIX

    def rate_limit(self, request_type):
        global first_request_date
        global request_timeout_seconds
        global requests_count
        global requests_limit
        if first_request_date is not None:
            current_timestamp = datetime.datetime.now()
            time_pass: datetime.timedelta = (
                current_timestamp - first_request_date
            )
            if time_pass.total_seconds() < request_timeout_seconds:
                if requests_count >= requests_limit:
                    waiting_time = (
                        request_timeout_seconds - time_pass.total_seconds()
                    )
                    logger.info(f"sleeping for {waiting_time} seconds")
                    time.sleep(waiting_time)
                    requests_count = 0
                    first_request_date = datetime.datetime.now()
                    request_timeout_seconds = None
            else:
                requests_count = 0
                first_request_date = datetime.datetime.now()
                request_timeout_seconds = None
        else:
            first_request_date = datetime.datetime.now()
        if request_type == "search":
            request_timeout_seconds = 10
            requests_limit = 10
        elif request_timeout_seconds is not None:
            request_timeout_seconds = max(request_timeout_seconds, 5)
            requests_limit = min(requests_limit, 30)
        else:
            request_timeout_seconds = 5
            requests_limit = 30

    def parseJSON(self, url=None, _type="images", trial_count=2) -> dict | None:
        global requests_count
        _id = None
        if url is not None and type(url) is int:
            _id = url
        else:
            _id = self.get_id_by_url(self._url)
        if type(_id) is not int:
            raise TypeError(f"ID: {_id} is not integer")
        data = None
        if self.get_origin_name() == ORIGIN:
            db_local_instance = make_connection()
            if db_local_instance is not None:
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
        if data is None:
            request_url = "https://{}/api/v1/json/{}/{}".format(
                self.get_domain_name_s(), _type, urllib.parse.quote(str(_id))
            )
            logger.debug("url: {}".format(url))
            logger.info("parseJSON: {}".format(request_url))
            self.rate_limit(_type)
            try:
                request_data = requests.get(request_url)
            except Exception as e:
                print(e)
                return
            finally:
                requests_count += 1
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
                "duplicate_of" in data["image"]
                and data["image"]["duplicate_of"] is not None
            ):
                data = self.parseJSON(str(data["image"]["duplicate_of"]))
        if "tags" not in data["image"]:
            data["image"]["tags"] = []
        self._parsed_data = data
        return data

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
        return self.file_deleted_handing(FILENAME_PREFIX, data["image"]["id"])

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
        if "name" in data and data["name"] is not None:
            name = "{}{} {}".format(
                self.get_filename_prefix(),
                data["id"],
                re.sub(
                    '[/\[\]:;|=*".?]', "", os.path.splitext(data["name"])[0]
                ),
            )
        else:
            name = "{}{}".format(self.get_filename_prefix(), data["id"])
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

    def get_raw_content_data(self):
        return self.get_data()["image"]

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
