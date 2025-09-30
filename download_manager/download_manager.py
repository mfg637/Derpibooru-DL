import abc
import logging
import os
import pathlib

import requests

import parser

ENABLE_REWRITING = False

logger = logging.getLogger(__name__)


class DownloadManager(abc.ABC):
    def __init__(self, _parser: parser.Parser.Parser):
        self.parser = _parser
        self._enable_rewriting = False
        self.source_file_data = None
        self.skip_download: bool = False

    def is_rewriting_allowed(self):
        return ENABLE_REWRITING or self._enable_rewriting

    def enable_rewriting(self):
        self._enable_rewriting = True

    def download_file(self, filename: pathlib.Path, src_url: str) -> None:
        logger.debug("download_file() call")
        request_data = requests.get(src_url)
        self.source_file_data = request_data.content
        file = open(filename, "wb")
        file.write(self.source_file_data)
        file.close()

    @abc.abstractmethod
    def _download_body(
        self,
        src_url: str,
        name: str,
        src_filename: pathlib.Path,
        output_directory: pathlib.Path,
        data: dict,
        tags: dict | None,
    ) -> tuple[int, int, int, int, pathlib.Path] | None:
        pass

    def download(
        self,
        output_directory: pathlib.Path,
        data: dict,
        tags: dict | None = None,
    ):
        logger.debug("download method execution")

        if self.parser.check_is_takedowned(data):
            return self.parser.get_takedowned_content_info(data)

        if not os.path.isdir(output_directory):
            os.makedirs(output_directory)

        src_url = self.parser.get_content_source_url(data)
        name, src_filename = self.parser.get_output_filename(
            data, output_directory
        )

        logger.info("filename: {}".format(src_filename))
        logger.debug("image_url: {}".format(src_url))

        result = self._download_body(
            src_url, name, src_filename, output_directory, data, tags
        )

        file_type: parser.Parser.FileTypes = self.parser.identify_filetype()
        if (
            file_type == parser.Parser.FileTypes.IMAGE
            and self.source_file_data is None
        ):
            if not self.skip_download:
                logger.debug("result: {}".format(result.__repr__()))
                self.parser.print_debug_info()
                raise ValueError("self.source_file_data IS NONE")
        logger.info(
            "Done downloading: {}{}".format(
                self.parser.get_filename_prefix(), self.parser.getID()
            )
        )

    def download_original_data(
        self,
        output_directory: pathlib.Path,
        data: dict,
        tags: dict | None = None,
    ):
        src_url = self.parser.get_content_source_url(data)
        name, src_filename = self.parser.get_output_filename(
            data, output_directory
        )

        logger.info("filename: {}".format(src_filename))
        logger.debug("image_url: {}".format(src_url))

        request_data = requests.get(src_url)
        result = {
            "mime": request_data.headers.get("content-type"),
            "data": request_data.content,
            "name": name,
        }

        return result

    def do_binary_request(self, url):
        logger.debug("do_binary_request() call, url={}".format(url))
        request_data = requests.get(url)
        self.source_file_data = request_data.content
        source = bytearray(self.source_file_data)
        return source
