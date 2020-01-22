#!/usr/bin/python3
# -*- coding: utf-8 -*- 

# root of download directory (your collection)
initial_dir = '/home/mfg637/Изображения/f/collections/drawings/ff/mlp/'

# user API key here
key = ''

# transcode PNG, JPEG, GIF images transcoding to WEBP, arithmetic JPEG, APNG formats
# required modules: Pillow, apng
# required programs: cwebp, jpegtran, ffmpeg
enable_images_optimisations = False

# Max webp image size
# works if image optimisations is enabled
# if value is None, set maximum possible for webp size
MAX_SIZE = None

# derpibooru-dl.py gui on/off
gui = True

enable_multiprocessing = False
