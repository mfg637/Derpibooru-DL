#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import argparse
import pathlib
import random
import time
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
import derpibooru_dl
import datamerge
from derpibooru_dl import tagResponse

derpibooru_dl.logging.init("server")

logger = logging.getLogger(__name__)

app = flask.Flask(__name__)
app.register_blueprint(datamerge.datamerge_blueprint)
error_message = None

map_list = list()

executed_tasks_titles = []
executing_tasks = []

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


dl_pool = download_manager.DownloadManager.create_pool(config.workers)


def append2queue_and_start_download(*args):
    global downloader_thread
    map_list.append(args)
    if not config.manual_start:
        if not downloader_thread.is_alive():
            downloader_thread = threading.Thread(target=async_downloader)
            downloader_thread.start()
    logger.info("download queue now contains {} requests".format(len(map_list)))


def async_downloader():
    global executing_tasks
    global executed_tasks_titles
    while len(map_list):
        local_map_list = map_list.copy()
        random.shuffle(local_map_list)
        map_list.clear()
        logger.info("processing {} requests".format(len(local_map_list)))
        executing_tasks.clear()
        executed_tasks_titles.clear()
        for task_arguments in local_map_list:
            dm: download_manager.DownloadManager = task_arguments[0]
            executed_tasks_titles.append(
                "{}{}".format(dm.parser.get_filename_prefix(), dm.parser.getID())
            )
        #results = dl_pool.map(download_manager.save_call, local_map_list, chunksize=1)
        results = []

        for task_arguments in local_map_list:
            task = dl_pool.apply_async(download_manager.save_call, (task_arguments,))
            executing_tasks.append(task)

        is_done = False
        tasks_number = len(executing_tasks)
        prev_tasks_ready = 0
        while not is_done:
            tasks_ready = 0
            is_done = True
            for task in executing_tasks:
                if task.ready():
                    tasks_ready += 1
                else:
                    is_done = False
            if tasks_ready != prev_tasks_ready:
                logger.info("ready {} tasks of {} total".format(tasks_ready, tasks_number))
                prev_tasks_ready = tasks_ready
            if not is_done:
                time.sleep(0.5)

        for task in executing_tasks:
            results.append(task.get())

        pyimglib.transcoding.statistics.update_stats(results)
    logger.info("Download is done! Waiting for new requests.")


@app.route('/do_download')
def do_download():
    global downloader_thread
    if config.manual_start:
        if not downloader_thread.is_alive():
            downloader_thread = threading.Thread(target=async_downloader)
            downloader_thread.start()
    return flask.render_template("do_download.html")


@app.route('/get_status.json')
def make_status_report():
    response_generator = zip(executed_tasks_titles, executing_tasks)
    response_document = []
    for i in response_generator:
        response_document.append({"title": i[0], "is_done": i[1].ready()})
    response = flask.Response(json.dumps(response_document))
    response.headers['content-type'] = "application/json"
    return response


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
            if not download_original_data:
                logger.info(
                    "Request for download: {}{}".format(
                        _parser.get_filename_prefix(),
                        content_id
                    )
                )
            data = _parser.parseJSON()
            logger.debug("received data: {}".format(data.__repr__()))
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
                if flask.request.method == 'POST':
                    return "OK"
                else:
                    return flask.render_template("response_ok.html")
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
        print("to download, go to http://{}:{}/do_download".format(config.webhost, config.port))
        app.run(host=config.host, port=config.port)
    except Exception as e:
        error_message = traceback.format_exc()
        logging.exception(error_message)
    finally:
        if config.do_transcode:
            import pyimglib.transcoding
            pyimglib.transcoding.statistics.log_stats()
        if args.test_medialib_db:
            medialib_db.testing.wipe()
