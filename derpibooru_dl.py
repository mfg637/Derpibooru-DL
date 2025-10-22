#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import pathlib

import config
import download_manager
import parser
import derpibooru_dl
from derpibooru_dl import tagResponse
import logging
import interactive_mode
import re

root_logger = logging.getLogger()
derpibooru_dl.logging.init(root_logger, "derpibooru_dl")

logger = logging.getLogger(__name__)


id_list = []
NO_GUI = False
id_type_regex = re.compile(r"^([a-z]{2})?\d+$")

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("id", help="derpibooru image ID", nargs="*")
arg_parser.add_argument(
    "--append",
    metavar="file",
    type=argparse.FileType("r"),
    help="read IDs from text file (one line - one ID)",
    default=None,
)
# arg_parser.add_argument(
# "--simulate", help="do not download actual image files", action="store_true")
arg_parser.add_argument(
    "--rewrite", help="force to rewrite existing files", action="store_true"
)
arg_parser.add_argument(
    "--no-gui", help="force to use CLI mode", action="store_true"
)
arg_parser.add_argument(
    "--deleted-list",
    help="list of deleted image's ID and it's tags",
    type=pathlib.Path,
    default=None,
    metavar="DELETED_LIST_FILE",
)
arg_parser.add_argument(
    "--response-cache-dir",
    metavar="CACHE DIRECTORY",
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

if args.loglevel:
    root_logger.setLevel(level=args.loglevel.upper())


id_list = args.id.copy()
rewrite = args.rewrite
download_manager.download_manager.ENABLE_REWRITING = rewrite
NO_GUI = args.no_gui
config.deleted_image_list_file_path = args.deleted_list
config.response_cache_dir = args.response_cache_dir

if args.append is not None:
    for line in args.append:
        id_list.append(line[:-1])
    args.append.close()


def download(url):
    try:
        _parser: parser.Parser.Parser = parser.get_parser(url)
    except parser.exceptions.NotBoorusPrefixError as e:
        logger.exception("invalid prefix in {}".format(e.url))
        exit(1)
    except parser.exceptions.SiteNotSupported as e:
        logger.exception("Site not supported {}".format(e.url))
        exit(1)
    try:
        data = _parser.get_data()
    except IndexError:
        exit(1)

    parsed_tags: dict = _parser.tags_processing()
    logger.debug("parsed tags: {}".format(parsed_tags.__repr__()))
    outdir = tagResponse.find_folder(parsed_tags)
    logger.info("output directory: {}".format(outdir))

    dm = download_manager.make_download_manager(_parser)
    if rewrite:
        dm.enable_rewriting()
    dm.download(outdir, data, parsed_tags)


if config.gui and not NO_GUI:
    import tkinter

    try:
        from derpibooru_dl import gui

        GUI = gui.GUI(id_list)
    except tkinter.TclError:
        config.gui = False


class ContentIdString(interactive_mode.types.ArgumentType[str]):
    def __init__(self):
        super().__init__("content_id")

    def parse_input(self, raw_value: str):
        test = id_type_regex.fullmatch(raw_value)
        if test is None:
            raise ValueError("Value is not content id")
        return raw_value


class DownloadByUrl(interactive_mode.Command):
    def __init__(self):
        super().__init__(
            command_name="url",
            command_aliases=[],
            command_description="Donload by HTTPS URL",
            required_arguments={"url": interactive_mode.types.HttpsUrlString()},
            optional_arguments={},
            args_position=["url"],
        )

    def execute(self, *required_arguments, **optional_arguments):
        arguments = self.arguments_processing(
            *required_arguments, **optional_arguments
        )
        url: str = arguments["url"]
        download(url)


class DownloadById(interactive_mode.Command):
    def __init__(self):
        super().__init__(
            command_name="id",
            command_aliases=[],
            command_description="Donload by content id",
            required_arguments={"id": ContentIdString()},
            optional_arguments={},
            args_position=["id"],
        )

    def execute(self, *required_arguments, **optional_arguments):
        arguments = self.arguments_processing(
            *required_arguments, **optional_arguments
        )
        content_id: str = arguments["id"]
        download(content_id)


if not config.gui or NO_GUI:
    if id_list:
        for current_id in id_list:
            download(current_id)
    else:
        im = interactive_mode.InteractiveEnvironment("id || url> ")
        im.add_command(DownloadByUrl())
        im.add_command(DownloadById())
        im.start()
