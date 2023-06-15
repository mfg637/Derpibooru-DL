import abc
import io
import json
import logging
import multiprocessing
import os
import pathlib
import sys
import threading

import PIL.Image
import pathvalidate
import requests
import imagehash

import config
import medialib_db
import parser
import pyimglib
import numpy

ENABLE_REWRITING = False

TEST_MEDIALIB = False

downloader_thread = threading.Thread()
download_queue = []

logger = logging.getLogger(__name__)

medialib_db_lock: multiprocessing.Lock = multiprocessing.Lock()


class DownloadManager(abc.ABC):
    def __init__(self, _parser: parser.Parser.Parser):
        self.parser = _parser
        self._enable_rewriting = False
        self.source_file_data = None

    def is_rewriting_allowed(self):
        return ENABLE_REWRITING or self._enable_rewriting

    def enable_rewriting(self):
        self._enable_rewriting = True

    def medialib_db_register(
            self,
            data,
            src_filename,
            transcoding_result,
            tags,
            file_type: parser.Parser.FileTypes,
            image_hash,
            connection
    ):
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
                    "Exception at content id={} from {}".format(data["id"], self.parser.get_origin_name())
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
                if file_type in {parser.Parser.FileTypes.IMAGE, parser.Parser.FileTypes.VECTOR_IMAGE}:
                    media_type = "image"
                elif file_type == parser.Parser.FileTypes.ANIMATION:
                    media_type = "video-loop"
                elif file_type == parser.Parser.FileTypes.VIDEO:
                    media_type = "video"
                else:
                    media_type = "image"
            _description = None
            content_id = None
            if "description" in data and len(data['description']):
                _description = data['description']
            try:
                content_id = medialib_db.srs_indexer.register(
                    pathlib.Path(outname),
                    _name,
                    media_type,
                    _description,
                    self.parser.get_origin_name(),
                    data["id"],
                    tags,
                    connection
                )
            except Exception as e:
                logger.exception(
                    "Exception at content id={} from {}".format(data["id"], self.parser.get_origin_name())
                )
                raise e
            if content_id is not None and image_hash is not None:
                medialib_db.set_image_hash(content_id, image_hash, connection)

    def medialib_db_update_tags(self, db_content_id, tags, connection):
        for tag_category in tags:
            _tag_category = tag_category
            if tag_category == 'original character' or tag_category == "characters":
                _tag_category = "character"
            for tag in tags[tag_category]:
                db_tag_id = medialib_db.tags_indexer.check_tag_exists(tag, _tag_category, connection)
                if db_tag_id is None:
                    db_tag_id = medialib_db.tags_indexer.insert_new_tag(tag, _tag_category, None, connection)
                medialib_db.connect_tag_by_id(db_content_id, db_tag_id, connection)

    def download_file(self, filename: pathlib.Path, src_url: str) -> None:
        request_data = requests.get(src_url)
        self.source_file_data = request_data.content
        file = open(filename, 'wb')
        file.write(self.source_file_data)
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

    @staticmethod
    def fix_filename(filename):
        name = pathvalidate.sanitize_filename(filename)
        name = name.replace("&", "-amp-")
        return name

    def download(self, output_directory: pathlib.Path, data: dict, tags: dict = None):
        global medialib_db_lock

        if self.parser.check_is_takedowned(data):
            return self.parser.get_takedowned_content_info(data)

        medialib_db_connection = None
        content_info = None
        if config.use_medialib_db:
            if TEST_MEDIALIB:
                medialib_db_connection = medialib_db.testing.make_connection()
            else:
                medialib_db_connection = medialib_db.common.make_connection()
            content_info = medialib_db.find_content_from_source(
                self.parser.get_origin_name(), self.parser.getID(), medialib_db_connection
            )
            if content_info is not None:
                self.medialib_db_update_tags(content_info[0], tags, medialib_db_connection)
                old_file_path = config.db_storage_dir.joinpath(content_info[1])
                if self.is_rewriting_allowed() and old_file_path.exists():
                    manifest_controller = None
                    if old_file_path.suffix == ".srs":
                        manifest_controller =\
                            pyimglib.transcoding.encoders.srs_image_encoder.SrsLossyImageEncoder(1, 0, 1)
                    elif old_file_path.suffix == ".mpd":
                        manifest_controller = pyimglib.transcoding.encoders.dash_encoder.DashVideoEncoder(1)
                    if manifest_controller is not None:
                        manifest_controller.set_manifest_file(old_file_path)
                        manifest_controller.delete_result()
                    else:
                        old_file_path.unlink(missing_ok=True)
                elif self.is_rewriting_allowed():
                    pass
                else:
                    medialib_db_connection.close()
                    return 0, 0, 0, 0

        if not os.path.isdir(output_directory):
            os.makedirs(output_directory)

        src_url = self.parser.get_content_source_url(data)
        name, src_filename = self.parser.get_output_filename(data, output_directory)

        if config.source_name_as_file_name:
            name = DownloadManager.fix_filename(name)
        else:
            name = "{}{}".format(self.parser.get_filename_prefix(), self.parser.getID())

        logger.info("filename: {}".format(src_filename))
        logger.debug("image_url: {}".format(src_url))

        result = self._download_body(
            src_url, name, src_filename, output_directory, data, tags
        )

        image_hash = None
        file_type: parser.Parser.FileTypes = self.parser.identify_filetype()
        if file_type == parser.Parser.FileTypes.IMAGE and self.source_file_data is not None:
            buffer = io.BytesIO(self.source_file_data)
            with PIL.Image.open(buffer) as img:
                image_hash = pyimglib.calc_image_hash(img)
        elif file_type == parser.Parser.FileTypes.IMAGE:
            raise ValueError("self.source_file_data IS NONE")

        if config.use_medialib_db:
            logger.debug("medialib-db acquire lock")
            medialib_db_lock.acquire(block=True)
            if content_info is not None:
                if result is not None:
                    medialib_db.update_file_path(
                        content_info[0], result[4], image_hash, medialib_db_connection
                    )
            else:
                if result is not None:
                    self.medialib_db_register(
                        self.parser.get_raw_content_data(),
                        src_filename,
                        result,
                        tags,
                        file_type,
                        image_hash,
                        medialib_db_connection
                    )
            medialib_db_connection.close()
            logger.debug("medialib-db release lock")
            medialib_db_lock.release()

        logger.info(
            "Done downloading: {}{}".format(self.parser.get_filename_prefix(), self.parser.getID())
        )

        if result is not None:
            return result[:4]
        else:
            return 0, 0, 0, 0

    def download_original_data(self, output_directory: pathlib.Path, data: dict, tags: dict = None):
        src_url = self.parser.get_content_source_url(data)
        name, src_filename = self.parser.get_output_filename(data, output_directory)

        name = DownloadManager.fix_filename(name)

        logger.info("filename: {}".format(src_filename))
        logger.debug("image_url: {}".format(src_url))

        request_data = requests.get(src_url)
        result = {"mime": request_data.headers.get('content-type'), "data": request_data.content, "name": name}

        return result

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

    def do_binary_request(self, url):
        request_data = requests.get(url)
        self.source_file_data = request_data.content
        source = bytearray(self.source_file_data)
        return source
