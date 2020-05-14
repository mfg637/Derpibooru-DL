#!/usr/bin/python3
# -*- coding: utf-8 -*- 

# root of download directory (your collection)
initial_dir = '/home/mfg637/Изображения/f/collections/drawings/ff/mlp/'

# user API key here
key = ''

# transcode PNG, JPEG, GIF images transcoding to WEBP, arithmetic JPEG, WEBM formats
# required modules: Pillow
# required programs: cwebp, jpegtran, ffmpeg
enable_images_optimisations = False

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

