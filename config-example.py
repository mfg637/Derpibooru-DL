#!/usr/bin/python3
# -*- coding: utf-8 -*- 

import enum

# root of download directory (your collection)
initial_dir = '/home/mfg637/Изображения/f/collections/drawings/ff/mlp/'

# user API key here
key = ''
twibooru_key = ''
ponybooru_key = ''

# transcode PNG, JPEG, GIF images transcoding to WEBP, arithmetic JPEG, WEBM formats
# required modules: Pillow
# required programs: cwebp, jpegtran, ffmpeg, cavif
enable_images_optimisations = False


class PREFERRED_CODEC(enum):
    WEBP = enum.auto()
    AVIF = enum.auto()


preferred_codec = PREFERRED_CODEC.WEBP

# if 0 or None, multithreading is off
# else, it's enables row-mt
avif_encoding_threads = 0

# Max webp image size
# works if image optimisations is enabled
# if value is None, set maximum possible for webp size
MAX_SIZE = None

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
mysql_host="localhost"
mysql_user=""
mysql_password=""
mysql_database=""

browser_tmpcache_directory = None

