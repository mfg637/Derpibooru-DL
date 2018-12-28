#!/usr/bin/python3
# -*- coding: utf-8 -*- 

import browser
import config

browser.gui.GUI()

if config.enable_images_optimisations:
    import derpibooru_dl.imgOptimizer
    derpibooru_dl.imgOptimizer.printStats()