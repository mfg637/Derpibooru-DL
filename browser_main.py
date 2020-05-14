#!/usr/bin/python3
# -*- coding: utf-8 -*- 

import browser
import config

try:
    browser.gui.GUI()
finally:
    if config.enable_images_optimisations:
        import derpibooru_dl.imgOptimizer
        derpibooru_dl.imgOptimizer.printStats()
    if config.use_mysql:
        from derpibooru_dl import tagResponse
        tagResponse.mysql_connection.close()