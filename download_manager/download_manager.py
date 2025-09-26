import abc
import dataclasses
import io
import json
import logging
import lzma
import multiprocessing
import os
import pathlib
import sys
import threading

import pathvalidate
import requests

import config
import parser

ENABLE_REWRITING = False

TEST_MEDIALIB = False

downloader_thread = threading.Thread()
download_queue = []

logger = logging.getLogger(__name__)

medialib_db_lock: multiprocessing.Lock = multiprocessing.Lock()


@dataclasses.dataclass
class ComfyUIWorkflow:
    prompt: dict
    workflow: dict


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

    @staticmethod
    def extract_attachments(metadata):
        plain_text_attachments: dict[str, str] = {}
        json_attachments: dict[str, any] = {}
        comfyUI_workflow: ComfyUIWorkflow | None = None
        xmp_metadata: str | None = None
        attachments = metadata
        if attachments:
            if "prompt" in attachments and "workflow" in attachments:
                comfyUI_workflow = ComfyUIWorkflow(
                    json.loads(attachments["prompt"]),
                    json.loads(attachments["workflow"]),
                )
            for key in attachments:
                if (
                    key in {"prompt", "workflow"}
                    and comfyUI_workflow is not None
                ):
                    continue
                else:
                    if "XML::XMP" in key:
                        xmp_metadata = attachments[key]
                    else:
                        parse_result = None
                        try:
                            parse_result = json.loads(attachments[key])
                        except json.decoder.JSONDecodeError:
                            plain_text_attachments[key] = attachments[key]
                        if parse_result is not None:
                            json_attachments[key] = parse_result
        return (
            plain_text_attachments,
            json_attachments,
            comfyUI_workflow,
            xmp_metadata,
        )

    @staticmethod
    def attachments_to_description(
        description: str, plain_text_attachments: dict[str, str], update: bool
    ) -> str:
        _description = description
        if _description is None:
            _description = "Attachments:\n"
        elif not update:
            _description += "\n" + "=" * 16 + "\nAttachments:\n"
        elif update:
            return description
        for key in plain_text_attachments:
            _description += f"{key}: {plain_text_attachments[key]}\n"
        return _description

    @staticmethod
    def detect_media_type(outname, file_type, srs_data=None) -> str:
        media_type = None
        if file_type in {
            parser.Parser.FileTypes.IMAGE,
            parser.Parser.FileTypes.VECTOR_IMAGE,
        }:
            media_type = "image"
        elif file_type == parser.Parser.FileTypes.ANIMATION:
            media_type = "video-loop"
        elif file_type == parser.Parser.FileTypes.VIDEO:
            media_type = "video"
        else:
            media_type = "image"
        return media_type

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
        src_url,
        name,
        src_filename,
        output_directory: pathlib.Path,
        data: dict,
        tags,
    ):
        pass

    @staticmethod
    def _init_pool(_lock):
        global medialib_db_lock
        medialib_db_lock = _lock

    @staticmethod
    def create_pool(workers: int):
        global medialib_db_lock

        medialib_db_lock = multiprocessing.Lock()
        return multiprocessing.Pool(
            processes=1,
            initializer=DownloadManager._init_pool,
            initargs=(medialib_db_lock,),
        )

    @staticmethod
    def fix_filename(filename):
        name = pathvalidate.sanitize_filename(filename)
        name = name.replace("&", "-amp-")
        return name

    def download(
        self, output_directory: pathlib.Path, data: dict, tags: dict = None
    ):
        global medialib_db_lock
        logger.debug("download method execution")

        if self.parser.check_is_takedowned(data):
            return self.parser.get_takedowned_content_info(data)

        medialib_db_connection = None
        content_info = None
        if not os.path.isdir(output_directory):
            os.makedirs(output_directory)

        src_url = self.parser.get_content_source_url(data)
        name, src_filename = self.parser.get_output_filename(
            data, output_directory
        )

        if config.source_name_as_file_name:
            name = DownloadManager.fix_filename(name)
        else:
            name = "{}{}".format(
                self.parser.get_filename_prefix(), self.parser.getID()
            )

        logger.info("filename: {}".format(src_filename))
        logger.debug("image_url: {}".format(src_url))

        result = self._download_body(
            src_url, name, src_filename, output_directory, data, tags
        )

        image_hash = None
        file_type: parser.Parser.FileTypes = self.parser.identify_filetype()
        if (
            file_type == parser.Parser.FileTypes.IMAGE
            and self.source_file_data is None
        ):
            if not self.skip_download:
                logger.debug("result: {}".format(result.__repr__()))
                self.parser.print_debug_info()
                raise ValueError("self.source_file_data IS NONE")
        image_format = self.parser.get_image_format(data)
        metadata = {}
        logger.info(
            "Done downloading: {}{}".format(
                self.parser.get_filename_prefix(), self.parser.getID()
            )
        )

        if result is not None:
            return result[:4]
        else:
            return 0, 0, 0, 0

    def download_original_data(
        self, output_directory: pathlib.Path, data: dict, tags: dict = None
    ):
        src_url = self.parser.get_content_source_url(data)
        name, src_filename = self.parser.get_output_filename(
            data, output_directory
        )

        name = DownloadManager.fix_filename(name)

        logger.info("filename: {}".format(src_filename))
        logger.debug("image_url: {}".format(src_url))

        request_data = requests.get(src_url)
        result = {
            "mime": request_data.headers.get("content-type"),
            "data": request_data.content,
            "name": name,
        }

        return result

    def save_image_old_interface(
        self,
        output_directory: pathlib.Path,
        data: dict,
        tags: dict = None,
        pipe=None,
    ) -> None:
        result = self.download(output_directory, data, tags)

    def append2queue(self, **kwargs):
        global downloader_thread
        global download_queue
        download_queue.append(kwargs)
        if not downloader_thread.is_alive():
            downloader_thread = threading.Thread(target=self.async_downloader)
            downloader_thread.start()

    def async_downloader(self):
        global download_queue
        while len(download_queue):
            print(
                "Queue: lost {} images".format(len(download_queue)),
                file=sys.stderr,
            )
            current_download = download_queue.pop()
            pipe = multiprocessing.Pipe()
            params = current_download
            params["pipe"] = pipe[1]
            process = multiprocessing.Process(
                target=self.save_image_old_interface, kwargs=params
            )
            process.start()
            process.join()
            print(
                "Queue: lost {} images".format(len(download_queue)),
                file=sys.stderr,
            )

    def do_binary_request(self, url):
        logger.debug("do_binary_request() call, url={}".format(url))
        request_data = requests.get(url)
        self.source_file_data = request_data.content
        source = bytearray(self.source_file_data)
        return source
