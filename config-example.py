#!/usr/bin/python3
# -*- coding: utf-8 -*- 

import pyimglib_transcoding.config

# root of download directory (your collection)
initial_dir = '*** insert your path required ***'

# user API key here
key = ''
twibooru_key = ''
ponybooru_key = ''

# derpibooru-dl.py gui on/off
gui = True

enable_multiprocessing = False

# Using database for tags info as key-value storage
use_mysql = False
# Create table command:
#CREATE TABLE `tag_categories` (
#  `tag` char(255) NOT NULL,
#  `category` enum('character','rating','species','content') DEFAULT NULL,
#  PRIMARY KEY (`tag`)
#) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
mysql_host = "localhost"
mysql_user = ""
mysql_password = ""
mysql_database = ""

browser_tmpcache_directory = None


# transcode PNG, JPEG, GIF images transcoding to WEBP, arithmetic JPEG, WEBM, AVIF formats
# required modules: Pillow
# required programs: cwebp, jpegtran, ffmpeg, cavif
enable_images_optimisations = False


pyimglib_transcoding.config.preferred_codec = pyimglib_transcoding.config.PREFERRED_CODEC.WEBP

# if 0 or None, multithreading is off
# else, it's enables row-mt
pyimglib_transcoding.config.avif_encoding_threads = 0

# Max image size
# works if image optimisations is enabled
# if value is None, set maximum possible for webp size
pyimglib_transcoding.config.MAX_SIZE = None
