#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
import pathlib
import random
import urllib.parse
import flask
import json
import traceback
import threading
import config
import download_manager
import medialib_db.common
import parser
import logging
import pyimglib
from derpibooru_dl import tagResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s::%(process)dx%(thread)d::%(levelname)s::%(name)s::%(message)s",
    datefmt="%M:%S"
)

logger = logging.getLogger(__name__)

app = flask.Flask(__name__)
error_message = None

map_list = list()

downloader_thread = threading.Thread()


FILE_SUFFIX_BY_MIME_TYPE = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "video/webm": "webm",
    "video/mp4": "mp4",
    "image/svg+xml": "svg"
}
FILE_SUFFIX_LIST = [
    ".png", ".jpg", ".gif", ".webm", ".mp4", ".svg"
]


def append2queue_and_start_download(*args):
    global downloader_thread
    map_list.append(args)
    logger.info("download queue now contains {} requests".format(len(map_list)))


def async_downloader():
    dl_pool = download_manager.DownloadManager.create_pool(config.workers)
    while len(map_list):
        local_map_list = map_list.copy()
        random.shuffle(local_map_list)
        map_list.clear()
        logger.info("processing {} requests".format(len(local_map_list)))
        results = dl_pool.map(download_manager.save_call, local_map_list, chunksize=1)
        pyimglib.transcoding.statistics.update_stats(results)
    logger.info("Download is done! Waiting for new requests.")


@app.route('/do_download')
def do_download():
    global downloader_thread
    if not downloader_thread.is_alive():
        downloader_thread = threading.Thread(target=async_downloader)
        downloader_thread.start()
    return "Download will start now!"


class RouteFabric:
    def __init__(self, _parser):
        self._parser = _parser

    def handle(self):
        global error_message
        try:
            content_id: int = flask.request.args.get("id", None, int)
            enable_rewriting: bool = flask.request.args.get("rewrite", False, bool)
            download_original_data: bool = flask.request.args.get("dl_orig", False, bool)
            if error_message is not None and not download_original_data:
                return error_message
            content_title: str = flask.request.args.get("title", None, str)
            print("content_id", content_id)
            content: dict = None
            if content_id is None:
                content = json.loads(flask.request.data.decode("utf-8"))
            _parser: parser.tag_indexer.TagIndexer = None
            logger.debug("received content: {}".format(content.__repr__()))
            if content_id is not None:
                pass
            elif 'imageId' in content:
                content_id = content['imageId']
            elif "id" in content:
                content_id = content['id']
            _parser = parser.tag_indexer.decorate(self._parser, config.use_medialib_db, content_id)
            data = _parser.parseJSON()
            parsed_tags = _parser.tagIndex()
            out_dir = tagResponse.find_folder(parsed_tags)
            _parser.dataValidator(data)
            dm = download_manager.make_download_manager(_parser)
            if enable_rewriting:
                dm.enable_rewriting()
            if download_original_data:
                original_data = dm.download_original_data(out_dir, data, parsed_tags)
                response = flask.Response(response=original_data["data"])
                name = original_data["name"]
                if content_title is not None:
                    for suffix in FILE_SUFFIX_LIST:
                        if suffix in content_title:
                            content_title = content_title.replace(suffix, "")
                    name = "{}{} {}.{}".format(
                        _parser.get_filename_prefix(),
                        _parser.getID(),
                        content_title.replace("-amp-", "&").replace("-eq-", "="),
                        FILE_SUFFIX_BY_MIME_TYPE[original_data["mime"]]
                    )
                response.headers['content-disposition'] = 'attachment; filename="{}"'.format(
                    urllib.parse.quote(name)
                )
                response.headers['content-type'] = original_data["mime"]
                return response
            else:
                append2queue_and_start_download(dm, out_dir, data, parsed_tags)
                return "OK"
        except Exception as e:
            error_message = traceback.format_exc()
            print(error_message)
            return error_message


@app.route('/', methods=['POST', 'GET'])
@app.route('/derpibooru', methods=['POST', 'GET'])
def derpibooru_handler():
    fabric = RouteFabric(parser.derpibooru.DerpibooruParser)
    return fabric.handle()


@app.route('/twibooru', methods=['POST', 'GET'])
def twibooru_handler():
    fabric = RouteFabric(parser.twibooru.TwibooruParser)
    return fabric.handle()


@app.route('/ponybooru', methods=['POST', 'GET'])
def ponybooru_handler():
    fabric = RouteFabric(parser.ponybooru.PonybooruParser)
    return fabric.handle()


@app.route('/furbooru', methods=['POST', 'GET'])
def furbooru_handler():
    fabric = RouteFabric(parser.furbooru.FurbooruParser)
    return fabric.handle()


@app.route('/e621', methods=['POST', 'GET'])
def e621_handler():
    fabric = RouteFabric(parser.e621.E621Parser)
    return fabric.handle()


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--home-path", help="where to download image files", type=pathlib.Path, default=None)
    arg_parser.add_argument("--test-medialib-db", action="store_true")
    args = arg_parser.parse_args()
    if args.home_path is not None:
        config.initial_dir = str(args.home_path)
    download_manager.download_manager.TEST_MEDIALIB = args.test_medialib_db
    try:
        print("accepting requests")
        print("to download, go to http://localhost:5757/do_download")
        app.run(host="localhost", port=5757)
    except Exception as e:
        error_message = traceback.format_exc()
        logging.exception(error_message)
    finally:
        if config.do_transcode:
            import pyimglib.transcoding
            pyimglib.transcoding.statistics.log_stats()
        if args.test_medialib_db:
            medialib_db.testing.wipe()
