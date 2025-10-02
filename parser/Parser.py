import abc
import datetime
import json
import logging
import pathlib
import time
import enum
import typing
import pathvalidate

import config

logger = logging.getLogger(__name__)


class FileTypes(enum.Enum):
    IMAGE = enum.auto()
    VECTOR_IMAGE = enum.auto()
    ANIMATION = enum.auto()
    VIDEO = enum.auto()


class RateLimiter(abc.ABC):
    def __init__(self):
        self.first_request_date: datetime.datetime | None = None
        self.request_timeout_seconds: int | None = None
        self.requests_count: int = 0
        self.requests_limit: int = 0

    @abc.abstractmethod
    def rate_limit(self, request_type):
        pass

    def increment_requests_count(self):
        self.requests_count += 1


class DummyRateLimiter(RateLimiter):
    def rate_limit(self, request_type):
        self.requests_count = 0


class OneRequestPerSecondRateLimiter(RateLimiter):
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
        self.request_timeout_seconds = 1
        self.requests_limit = 1


class Parser(abc.ABC):
    def __init__(self, url, parsed_data: dict | None = None):
        self._tag_indexer = None
        self._url = url
        self._parsed_data: dict | None = parsed_data

    def print_debug_info(self):
        print("origin name:", self.get_origin_name)
        print("URL:", self._url)
        print("parsed data", self._parsed_data)

    def _dump_parsed_data(self):
        if config.response_cache_dir is not None:
            config.response_cache_dir.mkdir(parents=True, exist_ok=True)
            f = config.response_cache_dir.joinpath(
                "{}{}.json".format(self.get_filename_prefix(), self.getID())
            ).open("w")
            if self._parsed_data is None:
                raise ValueError("self._parsed_data is None")
            serialized_data: dict = self._parsed_data.copy()
            for key in serialized_data:
                if key[:2] == "__":
                    serialized_data.pop(key)
            json.dump(serialized_data, f)
            f.close()

    def _load_parsed_data(self):
        self.input_id = self.get_id_by_url(self._url)
        if config.response_cache_dir is not None:
            if self.input_id[:2] == self.get_filename_prefix():
                self.input_id = self.input_id[2:]
            dump_file_path = config.response_cache_dir.joinpath(
                "{}{}.json".format(self.get_filename_prefix(), self.input_id)
            )
            if dump_file_path.exists():
                f = dump_file_path.open("r")
                self._parsed_data = json.load(f)
                f.close()
                logger.info("LOADED FROM DUMP")
                logger.debug(
                    "response_cache_dir={}, prefix={}, id={}, file_path={}".format(
                        config.response_cache_dir,
                        self.get_filename_prefix(),
                        self.input_id,
                        dump_file_path,
                    )
                )
                return self._parsed_data
        return None

    @staticmethod
    def get_id_by_url(URL) -> int:
        if type(URL) is str:
            intval = int(URL.split("?")[0].split("/")[-1])
            if type(intval) is int:
                return intval
            else:
                raise ValueError("Can't convert value to int")
        elif type(URL) is int:
            return URL
        else:
            raise ValueError("URL {} is {}".format(URL, type(URL)))

    @staticmethod
    def sanitise_filename(filename):
        name = pathvalidate.sanitize_filename(filename)
        name = name.replace("&", "-amp-")
        return name

    @abc.abstractmethod
    def get_content_id(self) -> int:
        pass

    @abc.abstractmethod
    def parseJSON(self, url=None, _type="images") -> dict | None:
        pass

    def get_data(self) -> dict:
        if self._parsed_data is None:
            data = self._load_parsed_data()
            if data is None:
                data = self.parseJSON()
                self._parsed_data = data
                if config.response_cache_dir is not None:
                    self._dump_parsed_data()
            if data is None:
                raise Exception("Unable to load data")
            return data
        else:
            return self._parsed_data

    @abc.abstractmethod
    def parsehtml_get_image_route_name(self) -> str:
        pass

    @abc.abstractmethod
    def get_domain_name(self) -> str:
        pass

    @abc.abstractmethod
    def getTagNamesList(self) -> list[str]:
        pass

    @abc.abstractmethod
    def getID(self) -> str:
        pass

    @abc.abstractmethod
    def dataValidator(self, data):
        pass

    @abc.abstractmethod
    def get_filename_prefix(self) -> str:
        pass

    @abc.abstractmethod
    def get_origin_name(self) -> str:
        pass

    @abc.abstractmethod
    def parseHTML(self, image_id) -> dict[str, str]:
        pass

    def get_auto_copyright_tags(self) -> set[str]:
        return set()

    def file_deleted_handing(self, prefix, _id):
        logging.exception("deleted image {}".format(_id))
        if config.deleted_image_list_file_path is not None:
            deleted_list_f = pathlib.Path(
                config.deleted_image_list_file_path
            ).open("a")
            parse_results = dict()
            try:
                parse_results = self.parseHTML(_id)
            except Exception as e:
                logger.exception("Some error was hapenned", e)
            deleted_list_f.write(
                "{}{}: {}\n".format(
                    prefix,
                    _id,
                    ", ".join([str(key) for key in parse_results.keys()]),
                )
            )
            deleted_list_f.close()
        return 0, 0, 0, 0

    @abc.abstractmethod
    def check_is_takedowned(self, data) -> bool:
        pass

    @abc.abstractmethod
    def get_takedowned_content_info(self, data) -> tuple:
        pass

    @abc.abstractmethod
    def get_content_source_url(self, data) -> str:
        pass

    @abc.abstractmethod
    def get_output_filename(
        self, data, output_directory
    ) -> tuple[str, pathlib.Path]:
        pass

    @abc.abstractmethod
    def get_image_metadata(self, data) -> dict:
        pass

    @abc.abstractmethod
    def get_image_format(self, data):
        pass

    @abc.abstractmethod
    def get_big_thumbnail_url(self, data):
        pass

    @abc.abstractmethod
    def get_raw_content_data(self):
        pass

    @abc.abstractmethod
    def identify_filetype(self) -> FileTypes:
        pass

    @staticmethod
    def identify_by_mimetype(mime_type: str) -> FileTypes:
        MIMETYPE_ASSOCIATIONS: typing.Final[dict[str, FileTypes]] = {
            "image/jpeg": FileTypes.IMAGE,
            "image/png": FileTypes.IMAGE,
            "image/gif": FileTypes.ANIMATION,
            "image/vnd.mozilla.apng": FileTypes.ANIMATION,
            "image/apng": FileTypes.ANIMATION,
            "video/webm": FileTypes.VIDEO,
            "video/mp4": FileTypes.VIDEO,
            "image/svg+xml": FileTypes.VECTOR_IMAGE,
        }
        return MIMETYPE_ASSOCIATIONS[mime_type]

    @abc.abstractmethod
    def tags_processing(self) -> dict[str, set[str]]:
        pass

    @abc.abstractmethod
    def make_rate_limiter(self) -> RateLimiter:
        pass
