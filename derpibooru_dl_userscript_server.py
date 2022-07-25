#!/usr/bin/python3
# -*- coding: utf-8 -*-

import flask
import json
import traceback
import threading
import config
import download_manager
import medialib_db.common
import parser
import multiprocessing
import logging
import pyimglib
from derpibooru_dl import tagResponse

logging.basicConfig(level=logging.INFO, format="%(process)dx%(thread)d::%(levelname)s::%(name)s::%(message)s")

logger = logging.getLogger(__name__)

app = flask.Flask(__name__)
error_message = None

map_list = list()

downloader_thread = threading.Thread()


def append2queue_and_start_download(*args):
    global downloader_thread
    map_list.append(args)
    logger.info("download queue now contains {} requests".format(len(map_list)))


def async_downloader():
    db_lock = multiprocessing.Lock()
    dl_pool = multiprocessing.Pool(
        processes=config.workers, initializer=medialib_db.common.db_lock_init, initargs=(db_lock,)
    )
    while len(map_list):
        local_map_list = map_list.copy()
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
            if error_message is not None:
                return error_message
            content: dict = json.loads(flask.request.data.decode("utf-8"))
            _parser: parser.tag_indexer.TagIndexer = None
            logger.debug("received content: {}".format(content.__repr__()))
            if 'imageId' in content:
                _parser = parser.tag_indexer.decorate(self._parser, config.use_medialib_db, content['imageId'])
            elif "id" in content:
                _parser = parser.tag_indexer.decorate(self._parser, config.use_medialib_db, content['id'])
            data = _parser.parseJSON()
            parsed_tags = _parser.tagIndex()
            out_dir = tagResponse.find_folder(parsed_tags)
            _parser.dataValidator(data)
            dm = download_manager.make_download_manager(_parser)
            append2queue_and_start_download(dm, out_dir, data, parsed_tags)
            return "OK"
        except Exception as e:
            error_message = traceback.format_exc()
            print(error_message)
            return error_message


@app.route('/', methods=['POST'])
def derpibooru_handler():
    fabric = RouteFabric(parser.derpibooru.DerpibooruParser)
    return fabric.handle()


@app.route('/twibooru', methods=['POST'])
def twibooru_handler():
    fabric = RouteFabric(parser.twibooru.TwibooruParser)
    return fabric.handle()


@app.route('/ponybooru', methods=['POST'])
def ponybooru_handler():
    fabric = RouteFabric(parser.ponybooru.PonybooruParser)
    return fabric.handle()


@app.route('/furbooru', methods=['POST'])
def furbooru_handler():
    fabric = RouteFabric(parser.furbooru.FurbooruParser)
    return fabric.handle()


@app.route('/e621', methods=['POST'])
def e621_handler():
    fabric = RouteFabric(parser.e621.E621Parser)
    return fabric.handle()


if __name__ == '__main__':
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
        if config.use_medialib_db:
            medialib_db.common.close_connection_if_not_closed()
