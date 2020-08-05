#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os, sys
from derpibooru_dl import tagResponse
import parser
import config


if config.enable_images_optimisations:
    from derpibooru_dl import imgOptimizer


id_list = []
i = 1
while i < len(sys.argv):
    if sys.argv[i][:2] == "--":
        if sys.argv[i][2:] == "append":
            i += 1
            file_path = sys.argv[i]
            file = open(file_path, 'r')
            for line in file:
                id_list.append(line[:-1])
            file.close()
    else:
        id_list.append(sys.argv[i])
    i += 1


def download(url):
    print('open connection')

    _parser = parser.get_parser(url)
    data = _parser.parseJSON()

    parsed_tags = tagResponse.tagIndex(_parser, data['image']['tags'])
    print("parsed tags", parsed_tags)
    outdir = tagResponse.find_folder(parsed_tags)
    print("outdir", outdir)

    if not os.path.isdir(outdir):
        os.makedirs(outdir)

    _parser.save_image(outdir, data['image'], parsed_tags)


try:
    if config.gui:
        import tkinter
        try:
            from derpibooru_dl import gui
            GUI = gui.GUI(id_list)
        except tkinter.TclError:
            config.gui = False

    if not config.gui:
        for id in id_list:
            download(id)

        while True:
            print("id||url>", end="")
            download(input())
finally:
    if config.enable_images_optimisations:
        imgOptimizer.printStats()
    if config.use_mysql:
        from derpibooru_dl import tagResponse
        parser.derpibooru.mysql_connection.close()
