#!/usr/bin/python3
# -*- coding: utf-8 -*- 

import browser
import config
import parser

try:
    browser.gui.GUI()
finally:
    if config.enable_images_optimisations:
        import pyimglib_transcoding
        pyimglib_transcoding.statistics.print_stats()
    if config.use_mysql:
        from derpibooru_dl import tagResponse
        parser.Parser.mysql_connection.close()
