#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import pathlib

import config
import download_manager
import medialib_db.common
import parser
from derpibooru_dl import tagResponse
import pyimglib
import logging

logging.basicConfig(
    format="%(process)dx%(thread)d::%(levelname)s::%(name)s::%(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

if config.do_transcode:
    import pyimglib.transcoding

id_list = []
NO_GUI = False

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("id", help="derpibooru image ID", nargs="*")
arg_parser.add_argument(
    "--append",
    metavar="file",
    type=argparse.FileType('r'),
    help="read IDs from text file (one line - one ID)",
    default=None
)
arg_parser.add_argument("--simulate", help="do not download actual image files", action="store_true")
arg_parser.add_argument("--rewrite", help="force to rewrite existing files", action="store_true")
arg_parser.add_argument("--no-gui", help="force to use CLI mode", action="store_true")
arg_parser.add_argument(
    "--deleted-list",
    help="list of deleted image's ID and it's tags",
    type=pathlib.Path,
    default=None,
    metavar="DELETED_LIST_FILE"
)
arg_parser.add_argument("--response-cache-dir", metavar="CACHE DIRECTORY", type=pathlib.Path, default=None)
arg_parser.add_argument(
    '-log',
    '--loglevel',
    default='warning',
    help='Provide logging level. Example --loglevel debug, default=warning'
)
args = arg_parser.parse_args()

if args.loglevel:
    logger.setLevel(level=args.loglevel.upper())


id_list = args.id.copy()
download_manager.download_manager.ENABLE_REWRITING = pyimglib.config.allow_rewrite = args.rewrite
config.simulate = args.simulate
NO_GUI = args.no_gui
config.deleted_image_list_file_path = args.deleted_list
config.response_cache_dir = args.response_cache_dir

if args.append is not None:
    for line in args.append:
        id_list.append(line[:-1])
    args.append.close()


def download(url):
    logger.debug('open connection')

    try:
        _parser: parser.tag_indexer.TagIndexer = parser.get_parser(url, config.use_medialib_db)
    except parser.exceptions.NotBoorusPrefixError as e:
        logger.exception("invalid prefix in {}".format(e.url))
        return
    except parser.exceptions.SiteNotSupported as e:
        logger.exception("Site not supported {}".format(e.url))
        return
    try:
        data = _parser.get_data()
    except IndexError:
        return

    parsed_tags: dict = _parser.tagIndex()
    logger.debug("parsed tags: {}".format(parsed_tags.__repr__()))
    outdir = tagResponse.find_folder(parsed_tags)
    logger.info("output directory: {}".format(outdir))

    dm = download_manager.make_download_manager(_parser)
    dm.save_image_old_interface(outdir, data, parsed_tags)


try:
    if config.gui and not NO_GUI:
        import tkinter
        try:
            from derpibooru_dl import gui
            GUI = gui.GUI(id_list)
        except tkinter.TclError:
            config.gui = False

    if not config.gui or NO_GUI:
        if id_list:
            for id in id_list:
                download(id)
        else:
            while True:
                print("id||url>", end="")
                download(input())
finally:
    if config.do_transcode:
        pyimglib.transcoding.statistics.log_stats()
