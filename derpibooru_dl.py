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

root_logger = logging.getLogger()
derpibooru_dl.logging.init(root_logger, "derpibooru_dl")

logger = logging.getLogger(__name__)


id_list = []
NO_GUI = False

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
    logger.debug("open connection")

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
    dm.save_image_old_interface(outdir, data, parsed_tags)


if config.gui and not NO_GUI:
    import tkinter

    try:
        from derpibooru_dl import gui

        GUI = gui.GUI(id_list)
    except tkinter.TclError:
        config.gui = False

if not config.gui or NO_GUI:
    if id_list:
        dl_pool = download_manager.DownloadManager.create_pool(1)
        dl_pool.map(download, id_list, chunksize=1)
    else:
        wait_for_command = True
        while wait_for_command:
            print("id || url> ", end="")
            command = input()
            if command in {"h", "help"}:
                print("h[elp]   show help message")
                print("q[uit]   exit from program")
                print("exit     exit from program")
                print("url or content id will be used for download")
            elif command in {"q", "quit", "exit"}:
                wait_for_command = False
            else:
                try:
                    check_id = parser.Parser.Parser.get_id_by_url(command)
                except ValueError:
                    print("invalid input: url or content id expected")
                    print("type h for help")
                else:
                    download(command)
