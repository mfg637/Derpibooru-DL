#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
import pathlib
import random
import flask
import json
import traceback
import threading
import config
import download_manager
import parser
import logging
import derpibooru_dl
import enum
import typing
import medialib_service
from derpibooru_dl import tagResponse
from pathlib import Path

root_logger = logging.getLogger()
root_logger.setLevel(logging.NOTSET)
derpibooru_dl.logging.init(root_logger, "server")
logger = logging.getLogger(__name__)

app = flask.Flask(__name__)
error_message = None


class TaskStatus(enum.StrEnum):
    AWAITING = "awaiting"
    EXECUTING = "executing"
    DONE = "done"


class Task:
    def __init__(
        self,
        dm: download_manager.DownloadManager,
        out_dir: pathlib.Path,
        data: dict,
        parsed_tags: dict[str, set[str]],
    ):
        self.dm = dm
        self.outdir = out_dir
        self.data = data
        self.parsed_tags = parsed_tags
        self.status = TaskStatus.AWAITING
        self.title = "{}{}".format(
            dm.parser.get_filename_prefix(), dm.parser.getID()
        )

    def __str__(self):
        return self.title

    def __repr__(self):
        return f"Task {self.title}: {self.status}"

    def get_title(self):
        return self.title

    def is_ready(self):
        return self.status is TaskStatus.DONE

    def execute(self):
        self.status = TaskStatus.EXECUTING
        self.dm.download(self.outdir, self.data, self.parsed_tags)
        medialib_service.prepare_and_send_result(
            self.dm, self.parsed_tags, self.data, self.outdir
        )
        # if config.use_medialib and not self.dm.skip_download:
        #     serializable_parsed_tags: dict[str, list[str]] = {
        #         category: list(self.parsed_tags[category])
        #         for category in self.parsed_tags
        #     }
        #     raw_data: dict = self.dm.parser.get_raw_content_data()
        #     content_title = raw_data.get("name", "")
        #     content_description = raw_data.get("description", "")
        #     response_data = {
        #         "origin_name": self.dm.parser.get_origin_name(),
        #         "origin_content_id": self.dm.parser.get_content_id(),
        #         "tags": serializable_parsed_tags,
        #         "output_filename": str(
        #             self.dm.parser.get_output_filename(self.data, self.outdir)[
        #                 1
        #             ]
        #         ),
        #         "title": content_title,
        #         "description": content_description,
        #         "mime_type": self.dm.parser.get_mime_type(),
        #     }
        #     status_message, is_ok = medialib_service.send_result(response_data)
        #     if is_ok:
        #         file_path = Path(response_data["output_filename"])
        #         file_path.unlink()
        self.status = TaskStatus.DONE


awaiting_tasks_list: list[Task] = list()


class TaskManager:
    def __init__(self):
        self.task_list: list[Task] = []

    def set_tasks(self, tasks: list[Task]):
        random.shuffle(tasks)
        del self.task_list
        self.task_list = tasks

    def execute_tasks(self):
        for task in self.task_list:
            task.execute()

    def make_status_report(self) -> list[dict[str, typing.Any]]:
        report = []
        for task in self.task_list:
            report.append(
                {"title": task.get_title(), "is_done": task.is_ready()}
            )
        return report

    def __str__(self):
        task_list = [task.__str__() for task in self.task_list]
        task_list_str = ", ".join(task_list)
        return f"TaskManager[{task_list_str}]"

    def __repr__(self):
        task_list = [task.__repr__() for task in self.task_list]
        task_list_str = ", ".join(task_list)
        return f"TaskManager[{task_list_str}]"


task_manager = TaskManager()
downloader_thread = threading.Thread()

FILE_SUFFIX_BY_MIME_TYPE = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "video/webm": "webm",
    "video/mp4": "mp4",
    "image/svg+xml": "svg",
}
FILE_SUFFIX_LIST = [".png", ".jpg", ".gif", ".webm", ".mp4", ".svg"]


def append2queue_and_start_download(
    dm: download_manager.DownloadManager,
    out_dir: pathlib.Path,
    data: dict,
    parsed_tags: dict[str, set[str]],
):
    global downloader_thread
    logger.debug('Starting "append2queue_and_start_download"')
    awaiting_tasks_list.append(Task(dm, out_dir, data, parsed_tags))
    if not config.manual_start:
        logger.debug("not manual start")
        if not downloader_thread.is_alive():
            logger.debug("downloading thread is not live")
            downloader_thread = threading.Thread(target=async_downloader)
            downloader_thread.start()
    logger.info(
        "download queue now contains {} requests".format(
            len(awaiting_tasks_list)
        )
    )


def async_downloader():
    logger.debug(
        f"awaiting_tasks_list contains {len(awaiting_tasks_list)} tasks"
    )
    while len(awaiting_tasks_list):
        local_map_list = awaiting_tasks_list.copy()
        task_manager.set_tasks(local_map_list)
        awaiting_tasks_list.clear()
        logger.info("processing {} requests".format(len(local_map_list)))
        task_manager.execute_tasks()

    logger.info("Download is done! Waiting for new requests.")


@app.route("/do_download")
def do_download():
    global downloader_thread
    if config.manual_start:
        if not downloader_thread.is_alive():
            downloader_thread = threading.Thread(target=async_downloader)
            downloader_thread.start()
    return flask.render_template("do_download.html")


@app.route("/get_status.json")
def make_status_report():
    response_document: list[dict[str, typing.Any]] = (
        task_manager.make_status_report()
    )
    return flask.jsonify(response_document)


class RouteFabric:
    def __init__(self, _parser):
        self._parser = _parser

    def handle(self):
        global error_message
        try:
            content_id: int | None = flask.request.args.get("id", None, int)
            enable_rewriting: bool = flask.request.args.get(
                "rewrite", False, bool
            )
            download_original_data: bool = flask.request.args.get(
                "dl_orig", False, bool
            )
            print("content_id", content_id)
            content: dict | None = None
            if content_id is None:
                content = json.loads(flask.request.data.decode("utf-8"))
            _parser: parser.Parser.Parser | None = None
            logger.debug("received content: {}".format(content.__repr__()))
            if content_id is not None:
                pass
            elif content is None:
                raise ValueError("content is still None")
            elif "imageId" in content:
                content_id = content["imageId"]
            elif "id" in content:
                content_id = content["id"]
            _parser = self._parser(content_id)
            if _parser is None:
                raise Exception("Failed to create a parser")
            if not download_original_data:
                logger.info(
                    "Request for download: {}{}".format(
                        _parser.get_filename_prefix(), content_id
                    )
                )
            data = _parser.parseJSON()
            if data is None:
                raise Exception(
                    (
                        f"Can't parse origin {_parser.get_origin_name()} "
                        f"with id = {content_id}"
                    )
                )
            logger.debug("received data: {}".format(data.__repr__()))
            parsed_tags = _parser.tags_processing()
            logger.debug("parsed tags: {}".format(parsed_tags.__repr__()))
            out_dir = tagResponse.find_folder(parsed_tags)
            logger.info(f"output directory: {out_dir}")
            _parser.dataValidator(data)
            dm = download_manager.make_download_manager(_parser)
            if enable_rewriting:
                dm.enable_rewriting()
            if error_message is None:
                append2queue_and_start_download(dm, out_dir, data, parsed_tags)
            serializable_parsed_tags: dict[str, list[str]] = {
                category: list(parsed_tags[category])
                for category in parsed_tags
            }
            raw_data: dict = _parser.get_raw_content_data()
            response_data = {
                "origin_name": _parser.get_origin_name(),
                "origin_domain_name": _parser.get_domain_name(),
                "origin_content_id": _parser.get_content_id(),
                "tags": serializable_parsed_tags,
                "output_directory": str(out_dir),
                "output_filename": str(
                    _parser.get_output_filename(data, out_dir)[1]
                ),
                "image_format": _parser.get_image_format(data),
                "status": "OK" if error_message is None else error_message,
                "raw_data": raw_data,
            }
            response_object = flask.jsonify(response_data)
            if error_message is not None:
                response_object.status_code = 500
            return response_object
        except Exception:
            error_message = traceback.format_exc()
            print(error_message)
            response_data = {"status": error_message}
            return flask.jsonify(response_data, status_code=500)


@app.route("/", methods=["POST", "GET"])
@app.route("/derpibooru", methods=["POST", "GET"])
def derpibooru_handler():
    fabric = RouteFabric(parser.derpibooru.DerpibooruParser)
    return fabric.handle()


@app.route("/twibooru", methods=["POST", "GET"])
def twibooru_handler():
    fabric = RouteFabric(parser.twibooru.TwibooruParser)
    return fabric.handle()


@app.route("/ponybooru", methods=["POST", "GET"])
def ponybooru_handler():
    fabric = RouteFabric(parser.ponybooru.PonybooruParser)
    return fabric.handle()


@app.route("/furbooru", methods=["POST", "GET"])
def furbooru_handler():
    fabric = RouteFabric(parser.furbooru.FurbooruParser)
    return fabric.handle()


@app.route("/e621", methods=["POST", "GET"])
def e621_handler():
    fabric = RouteFabric(parser.e621.E621Parser)
    return fabric.handle()


@app.route("/tantabus", methods=["POST", "GET"])
def tantabus_handler():
    fabric = RouteFabric(parser.tantabus.TantabusAIParser)
    return fabric.handle()


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--home-path",
        help="where to download image files",
        type=pathlib.Path,
        default=None,
    )
    arg_parser.add_argument(
        "-log",
        "--loglevel",
        default="notset",
        help="Provide logging level. Example --loglevel debug, default=notset",
    )
    args = arg_parser.parse_args()
    if args.home_path is not None:
        config.initial_dir = str(args.home_path)
    if args.loglevel:
        root_logger.setLevel(level=args.loglevel.upper())
    try:
        print("accepting requests")
        print(
            "to download, go to http://{}:{}/do_download".format(
                config.webhost, config.port
            )
        )
        app.run(host=config.host, port=config.port)
    except Exception:
        error_message = traceback.format_exc()
        logging.exception(error_message)
