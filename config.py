#!/usr/bin/python3
# -*- coding: utf-8 -*-
import pathlib
import enum
from dotenv import load_dotenv
import os

load_dotenv()

host = "localhost"
webhost = host
port = 5757

# root of download directory (your collection)
initial_dir = pathlib.Path(os.getenv(
    "DDL_initial_dir", "*** insert your path here ***"
))

class PathSpecification(enum.Enum):
    COLLECTION = enum.auto()
    DATE_DOWNLOADED = enum.auto()

saving_path: PathSpecification = PathSpecification.COLLECTION

# user API key here
key = os.getenv("DERPIBOORU_API_KEY", "")
twibooru_key = os.getenv("TWIBOORU_API_KEY", "")
ponybooru_key = os.getenv("PONYBOORU_API_KEY", "")
e621_login = os.getenv("E621_LOGIN", None)
e621_API_KEY = os.getenv("E621_API_KEY", None)

# derpibooru-dl.py gui on/off
gui = False

# TODO: what this option does?
source_name_as_file_name = True

response_cache_dir = None

# TODO: what is this option for?
deleted_image_list_file_path = None

# TODO: what is this option for?
manual_start = False
