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
initial_dir = pathlib.Path(
    os.getenv("DDL_initial_dir", "*** insert your path here ***")
)


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

# this option indicates to use file name from API or not
# affected on philomena based boorus
source_name_as_file_name = True

max_name_length = 128

response_cache_dir = None

# TODO: what is this option for?
deleted_image_list_file_path = None

# TODO: what is this option for?
manual_start = False

simulate = False

db_user = os.getenv("DDL_DB_USER", None)
db_password = os.getenv("DDL_DB_PASSWORD", None)
app_db_host = os.getenv("DDL_DB_HOST", None)
app_db_prod = os.getenv("DDL_DB_PROD", None)
app_db_test = os.getenv("DDL_DB_TEST", None)
derpibooru_dump_db_host = os.getenv("DERPIBOORU_DUMP_HOST", None)
derpibooru_dump_db_user = os.getenv("DERPIBOORU_DUMP_USER", db_user)
derpibooru_dump_db_password = os.getenv("DERPIBOORU_DUMP_PASSWORD", db_password)
