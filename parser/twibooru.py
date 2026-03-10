import logging
import datetime
from dateutil import tz
import time
import urllib.parse
import pathlib
import requests
import json
import os
import re
import config
from . import philomena, Parser

logger = logging.getLogger(__name__)

FILENAME_PREFIX = "tb"
ORIGIN = "twibooru"


RESET_PERIOD = datetime.timedelta(minutes=1)
LIMITER_BIAS = datetime.timedelta(seconds=30)


class TwibooruRateLimiter(Parser.RateLimiter):
    def __init__(self):
        super().__init__()
        self.reset_time: datetime.datetime | None = None
        self.requests_remaining: int = 60

    def rate_limit(self, request_type):
        if self.first_request_date is not None:
            current_timestamp = datetime.datetime.now()
            time_pass: datetime.timedelta = (
                current_timestamp - self.first_request_date
            )
            if self.reset_time is None:
                pass
            elif current_timestamp < self.reset_time:
                if not self.requests_remaining:
                    waiting_time = self.reset_time - current_timestamp
                    logger.info(f"sleeping for {waiting_time} seconds")
                    time.sleep(waiting_time.total_seconds())
                    self.requests_count = 0
                    self.requests_remaining = -1
                    self.first_request_date = datetime.datetime.now()
                    self.request_timeout_seconds = None
                    self.reset_time = self.first_request_date + RESET_PERIOD
            else:
                self.requests_count = 0
                self.first_request_date = datetime.datetime.now()
                self.request_timeout_seconds = None
                self.requests_remaining = 60
                self.reset_time = (
                    self.first_request_date + RESET_PERIOD + LIMITER_BIAS
                )
        else:
            self.first_request_date = datetime.datetime.now()
        self.request_timeout_seconds = 60
        if request_type == "search":
            self.requests_limit = 10
        elif self.request_timeout_seconds is not None:
            self.requests_limit = min(self.requests_limit, 60)
        else:
            self.requests_limit = 60

    @staticmethod
    def parse_utc_time(utcdatetimestring: str) -> datetime.datetime:
        date_str = utcdatetimestring.replace(" UTC", "")
        dt_naive = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        dt_utc = dt_naive.replace(tzinfo=datetime.timezone.utc)
        local_tz = tz.gettz()
        dt_local = dt_utc.astimezone(local_tz)
        return dt_local.replace(tzinfo=None)

    def update_rate_limit(self, response_headers):
        self.reset_time = (
            self.parse_utc_time(response_headers["x-rl-reset"]) + LIMITER_BIAS
        )
        self.requests_limit = min(
            int(response_headers["x-rl"]), self.requests_limit
        )
        self.requests_remaining = min(
            int(response_headers["x-rl-remain"]), self.requests_remaining
        )
        self.requests_count = self.requests_limit - self.requests_remaining


class TwibooruParser(philomena.Philomena):
    @staticmethod
    def get_domain_name_s():
        return "twibooru.org"

    def get_filename_prefix(self):
        return FILENAME_PREFIX

    def get_origin_name(self):
        return ORIGIN

    def get_domain_name(self) -> str:
        return TwibooruParser.get_domain_name_s()

    def custom_tag_processing(self):
        return None

    def custom_data_loading(
        self, _id: int, request_type="images"
    ) -> dict | None:
        return None

    def get_auto_copyright_tags(self) -> set[str]:
        return {"my little pony"}

    def make_rate_limiter(self):
        return TwibooruRateLimiter()

    def parseJSON(
        self, url=None, _type="posts", trial_count=2, **query_params
    ) -> dict | None:
        _id = None
        if url is not None:
            _id = url
        else:
            _id = self.get_id_by_url(self._url)
        if _id is None:
            raise TypeError(f"ID: {_id} is still None")
        data: dict | None = None
        if data is None:
            url_path = (
                pathlib.PurePosixPath("/api/v3/")
                .joinpath(_type)
                .joinpath(urllib.parse.quote(str(_id)))
            )
            request_url_object = urllib.parse.ParseResult(
                "https",
                self.get_domain_name_s(),
                str(url_path),
                "",
                urllib.parse.urlencode(query_params),
                "",
            )
            request_url = urllib.parse.urlunparse(request_url_object)
            logger.debug("url: {}".format(url))
            logger.info("parseJSON: {}".format(request_url))
            self.rate_limiter.rate_limit(_type)
            try:
                request_data = requests.get(request_url)
            except Exception as e:
                self.rate_limiter.increment_requests_count()
                print(e)
                return
            else:
                self.rate_limiter.increment_requests_count()
                if isinstance(self.rate_limiter, TwibooruRateLimiter):
                    self.rate_limiter.update_rate_limit(request_data.headers)
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
                and _type == "posts"
                and "duplicate_of" in data["post"]
                and data["post"]["duplicate_of"] is not None
            ):
                data = self.parseJSON(str(data["post"]["duplicate_of"]))
        if data is not None and _type == "posts" and "tags" not in data["post"]:
            data["post"]["tags"] = []
        if _type == "post":
            self._parsed_data = data
        return data

    def enable_html_parsing(self) -> bool:
        return False

    def parseHTML(self, image_id) -> dict[str, str]:
        raise Exception("ParseHTML is disabled for Twibooru")

    def dataValidator(self, data):
        if "post" not in data:
            raise KeyError("data has no 'post'")
        data = data["post"]
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
            "deletion_reason" in data["post"]
            and data["post"]["deletion_reason"] is not None
        )

    def get_takedowned_content_info(self, data):
        return self.file_deleted_handing(
            self.get_filename_prefix(), data["post"]["id"]
        )

    def get_content_source_url(self, data) -> str:
        representation_url_string = data["post"]["representations"]["full"]
        representation_url_object = urllib.parse.urlparse(
            representation_url_string
        )
        url_path_component = pathlib.PurePosixPath(
            representation_url_object.path
        )
        url_path_with_new_suffix = url_path_component.with_suffix(
            ".{}".format(data["post"]["format"].lower())
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
        name = Parser.Parser.sanitise_filename(name)
        return name, output_directory.joinpath(
            "{}.{}".format(name, data["format"].lower())
        )

    def get_image_metadata(self, data):
        return {
            "title": data["post"]["name"],
            "origin": self.get_origin_name(),
            "id": data["post"]["id"],
        }

    def get_image_format(self, data):
        return data["post"]["format"]

    def get_big_thumbnail_url(self, data):
        return data["image"]["representations"]["large"]

    def get_raw_content_data(self):
        return self.get_data()["post"]
