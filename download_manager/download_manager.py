import abc
import io
import json
import logging
import multiprocessing
import os
import pathlib
import sys
import threading

import requests

import config
import medialib_db
import parser
import pyimglib

ENABLE_REWRITING = False

downloader_thread = threading.Thread()
download_queue = []

logger = logging.getLogger(__name__)

medialib_db_lock: multiprocessing.Lock = multiprocessing.Lock()


class DownloadManager(abc.ABC):
    def __init__(self, _parser: parser.Parser.Parser):
        self._parser = _parser
        self._enable_rewriting = False

    def is_rewriting_allowed(self):
        return ENABLE_REWRITING or self._enable_rewriting

    def enable_rewriting(self):
        self._enable_rewriting = True

    def medialib_db_register(self, data, src_filename, transcoding_result, tags, connection):
        if config.simulate:
            return
        outname: pathlib.Path = src_filename
        if transcoding_result is not None:
            try:
                outname = transcoding_result[4]
                if type(outname) is io.TextIOWrapper:
                    outname = pathlib.Path(outname.name)
            except IndexError as e:
                logger.exception(
                    "Exception at content id={} from {}".format(data["id"], self._parser.get_origin_name())
                )
                raise e
        elif not outname.exists():
            logger.error("NOT FOUNDED FILE")
            raise FileNotFoundError()

        _name = None
        media_type = None
        if 'name' in data:
            _name = data['name']
        if outname is not None:
            if outname.suffix == ".srs":
                f = open(outname, "r")
                _data = json.load(f)
                f.close()
                media_type = medialib_db.srs_indexer.MEDIA_TYPE_CODES[_data['content']['media-type']]
            else:
                out_path = pathlib.Path(outname)
                if out_path.suffix.lower() in {".jpeg", ".jpg", ".png", ".webp", ".jxl", ".avif"}:
                    media_type = "image"
                elif out_path.suffix.lower() == ".gif":
                    media_type = "video-loop"
                elif out_path.suffix.lower() in {'.webm', ".mp4", ".mpd"}:
                    media_type = "video"
                else:
                    media_type = "image"
            _description = None
            if "description" in data and len(data['description']):
                _description = data['description']
            try:
                medialib_db.srs_indexer.register(
                    pathlib.Path(outname),
                    _name,
                    media_type,
                    _description,
                    self._parser.get_origin_name(),
                    data["id"],
                    tags,
                    connection
                )
            except Exception as e:
                logger.exception(
                    "Exception at content id={} from {}".format(data["id"], self._parser.get_origin_name())
                )
                raise e

    @staticmethod
    def download_file(filename: pathlib.Path, src_url: str) -> None:
        request_data = requests.get(src_url)
        file = open(filename, 'wb')
        file.write(request_data.content)
        file.close()

    @abc.abstractmethod
    def _download_body(self, src_url, name, src_filename, output_directory: pathlib.Path, data: dict, tags):
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
            processes=config.workers, initializer=DownloadManager._init_pool, initargs=(medialib_db_lock,)
        )

    def download(self, output_directory: pathlib.Path, data: dict, tags: dict = None):
        global medialib_db_lock

        if self._parser.verify_not_takedowned(data):
            return self._parser.get_takedowned_content_info(data)

        medialib_db_connection = None
        content_info = None
        if config.use_medialib_db:
            medialib_db_connection = medialib_db.common.make_connection()
            content_info = medialib_db.find_content_from_source(
                self._parser.get_origin_name(), self._parser.getID(), medialib_db_connection
            )
            if content_info is not None:
                old_file_path = config.db_storage_dir.joinpath(content_info[1])
                if self.is_rewriting_allowed() and old_file_path.exists():
                    files: list[pathlib.Path] = []
                    if old_file_path.suffix == ".srs":
                        files.extend(pyimglib.decoders.srs.get_file_paths(old_file_path))
                    elif old_file_path.suffix == ".mpd":
                        pyimglib.transcoding.encoders.dash_encoder.DASHEncoder.delete_result(old_file_path)
                    files.append(old_file_path)
                    for file in files:
                        file.unlink(missing_ok=True)
                elif self.is_rewriting_allowed():
                    pass
                else:
                    medialib_db_connection.close()
                    return 0, 0, 0, 0

        if not os.path.isdir(output_directory):
            os.makedirs(output_directory)

        src_url = self._parser.get_content_source_url(data)
        name, src_filename = self._parser.get_output_filename(data, output_directory)

        logger.info("filename: {}".format(src_filename))
        logger.debug("image_url: {}".format(src_url))

        result = self._download_body(src_url, name, src_filename, output_directory, data, tags)

        if config.use_medialib_db:
            medialib_db_lock.acquire(block=True)
            if content_info is not None:
                if result is not None:
                    medialib_db.update_file_path(
                        content_info[0], str(result[4].relative_to(config.db_storage_dir)), medialib_db_connection
                    )
            else:
                if result is not None:
                    self.medialib_db_register(
                        self._parser.get_raw_content_data(), src_filename, result, tags, medialib_db_connection
                    )
            medialib_db_connection.close()
            medialib_db_lock.release()

        if result is not None:
            return result[:4]
        else:
            return 0, 0, 0, 0

    def save_image_old_interface(self, output_directory: pathlib.Path, data: dict, tags: dict = None, pipe=None) -> None:
        result = self.download(output_directory, data, tags)
        if pipe is not None:
            pipe.send(
                (
                    pyimglib.transcoding.statistics.sumos + result[0],
                    pyimglib.transcoding.statistics.sumsize + result[1],
                    pyimglib.transcoding.statistics.avq + result[2],
                    pyimglib.transcoding.statistics.items + result[3]
                )
            )
            pipe.close()

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
            print("Queue: lost {} images".format(len(download_queue)), file=sys.stderr)
            current_download = download_queue.pop()
            pipe = multiprocessing.Pipe()
            params = current_download
            params['pipe'] = pipe[1]
            process = multiprocessing.Process(target=self.save_image_old_interface, kwargs=params)
            process.start()
            import pyimglib.transcoding.statistics as stats
            stats.sumos, stats.sumsize, stats.avq, stats.items = pipe[0].recv()
            process.join()
            print("Queue: lost {} images".format(len(download_queue)), file=sys.stderr)

    def in_memory_transcode(self, src_url, name, output_directory, force_lossless=False):
        source = self.do_binary_request(src_url)
        transcoder = pyimglib.transcoding.get_memory_transcoder(
            source, output_directory, name, force_lossless
        )
        return transcoder.transcode()

    @staticmethod
    def do_binary_request(url):
        request_data = requests.get(url)
        source = bytearray(request_data.content)
        return source
