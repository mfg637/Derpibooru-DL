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