#!/usr/bin/python3
# -*- coding: utf-8 -*-
import pathlib

import pyimglib.config

# root of download directory (your collection)
initial_dir = '*** insert your path required ***'
db_storage_dir = pathlib.Path()

# user API key here
key = ''
twibooru_key = ''
ponybooru_key = ''
e621_login = None
e621_API_KEY = None

# derpibooru-dl.py gui on/off
gui = True

enable_multiprocessing = False

# Using database for tags info as key-value storage
use_medialib_db = False

source_name_as_file_name = True


# transcode PNG, JPEG, GIF images transcoding to WEBP, arithmetic JPEG, WEBM, AVIF formats
# required modules: Pillow
# required programs: cwebp, jpegtran, ffmpeg, cavif, cjxl(JPEG XL reference encoder)
do_transcode = False

simulate = False
response_cache_dir = None

workers = 1

# None or constant string
deleted_image_list_file_path = None

if do_transcode:
    # if 0 or None, multithreading is off
    # else, it's enables row-mt
    pyimglib.config.encoding_threads = 0

    # Max image size
    # if value is None, set maximum possible for webp size
    pyimglib.config.MAX_SIZE = None

    # if none, use JPEG's Arithmetic coding
    # if not none, use JPEG XL's lossless encoding
    pyimglib.config.jpeg_xl_tools_path = None

