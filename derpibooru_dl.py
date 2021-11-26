#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os

import argparse
import pathlib

import config
import parser
from derpibooru_dl import tagResponse
import pyimglib
import logging

logging.basicConfig(level=logging.INFO, format="%(process)dx%(thread)d::%(levelname)s::%(name)s::%(message)s")

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
args = arg_parser.parse_args()

id_list = args.id.copy()
parser.Parser.ENABLE_REWRITING = pyimglib.config.allow_rewrite = args.rewrite
config.simulate = args.simulate
NO_GUI = args.no_gui
config.deleted_image_list_file_path = args.deleted_list

if args.append is not None:
    for line in args.append:
        id_list.append(line[:-1])
    args.append.close()


def download(url):
    print('open connection')

    _parser = parser.get_parser(url)
    try:
        data = _parser.parseJSON()
    except IndexError:
        return

    parsed_tags = _parser.tagIndex()
    print("parsed tags", parsed_tags)
    outdir = tagResponse.find_folder(parsed_tags)
    print("outdir", outdir)

    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    _parser.save_image_old_interface(outdir, data, parsed_tags)


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
    if config.use_mysql:
        parser.Parser.mysql_connection.close()
