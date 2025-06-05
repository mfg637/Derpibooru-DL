import abc
import json
import logging
import pathlib
import sys
import enum
import typing
from html.parser import HTMLParser

import requests

import config

logger = logging.getLogger(__name__)


class FileTypes(enum.Enum):
    IMAGE = enum.auto()
    VECTOR_IMAGE = enum.auto()
    ANIMATION = enum.auto()
    VIDEO = enum.auto()


class Parser(abc.ABC):
    def __init__(self, url, parsed_data=None):
        self._tag_indexer = None
        self._url = url
        self._parsed_data = parsed_data

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
            json.dump(self._parsed_data, f)
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
                        dump_file_path
                    )
                )
                return self._parsed_data
        return None

    @staticmethod
    def get_id_by_url(URL):
        if type(URL) is str:
            return URL.split('?')[0].split('/')[-1]
        elif type(URL) is int:
            return URL
        else:
            ValueError("URL {} is {}".format(URL, type(URL)))

    @abc.abstractmethod
    def parseJSON(self, url=None, _type="images") -> dict:
        pass

    def get_data(self):
        if self._parsed_data is None:
            data = self._load_parsed_data()
            if data is None:
                data = self.parseJSON()
                self._parsed_data = data
                if config.response_cache_dir is not None:
                    self._dump_parsed_data()
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
    def getTagList(self) -> list:
        pass

    @abc.abstractmethod
    def getID(self) -> str:
        pass

    @abc.abstractmethod
    def dataValidator(self, data):
        pass

    @abc.abstractmethod
    def get_filename_prefix(self):
        pass

    @abc.abstractmethod
    def get_origin_name(self):
        pass

    def parseHTML(self, image_id) -> dict:
        """
        Parse tags by HTML page.
        :param image_id:
        :return: {"tag name 1": "tag category 1", …}
        """
        global tags_parsed_data
        # derpibooru's API didn't provide method to get tag slug
        # image route also didn't contain that data
        tags_parsed_data = dict()
        request_url = 'https://{}/{}/{}'.format(
            self.get_domain_name(),
            self.parsehtml_get_image_route_name(),
            image_id
        )
        print("parseHTML", request_url, file=sys.stderr)
        try:
            request_data = requests.get(request_url)
        except Exception as e:
            print(e, file=sys.stderr)
            return
        raw_html = request_data.text

        class TagsParser(HTMLParser):
            def error(self, message):
                raise Exception(message)

            def handle_starttag(self, tag, attrs):
                if tag == 'div':
                    attributes = dict(attrs)
                    if "data-tag-name" in attributes.keys() and "data-tag-category" in attributes.keys():
                        tags_parsed_data[attributes["data-tag-name"]] = attributes["data-tag-category"]

        parser = TagsParser()
        parser.feed(raw_html)
        return tags_parsed_data

    def get_auto_copyright_tags(self):
        return {"my little pony"}


    def file_deleted_handing(self, prefix, _id):
        logging.exception("deleted image {}".format(_id))
        if config.deleted_image_list_file_path is not None:
            deleted_list_f = pathlib.Path(config.deleted_image_list_file_path).open("a")
            parse_results = dict()
            try:
                parse_results = self.parseHTML(_id)
            except Exception as e:
                logger.exception("Some error was hapenned", e)
            deleted_list_f.write("{}{}: {}\n".format(
                prefix, _id, ", ".join([str(key) for key in parse_results.keys()])
            ))
            deleted_list_f.close()
        return 0, 0, 0, 0


    @abc.abstractmethod
    def check_is_takedowned(self, data):
        pass

    @abc.abstractmethod
    def get_takedowned_content_info(self, data):
        pass

    @abc.abstractmethod
    def get_content_source_url(self, data):
        pass

    @abc.abstractmethod
    def get_output_filename(self, data, output_directory) -> tuple[str, pathlib.Path]:
        pass

    @abc.abstractmethod
    def get_image_metadata(self, data):
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
            "image/svg+xml": FileTypes.VECTOR_IMAGE
        }
        return MIMETYPE_ASSOCIATIONS[mime_type]
