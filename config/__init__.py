#!/usr/bin/python3
# -*- coding: utf-8 -*-
import pathlib
from dotenv import load_dotenv
import os
import json
from .definitions import PathSpecification

load_dotenv()


def _init() -> dict:
    config_data = {}
    app_dir = pathlib.Path(os.path.dirname(os.path.realpath(__file__))).parent
    config_file_json = app_dir.joinpath("config.json")
    if config_file_json.is_file():
        with config_file_json.open("r") as f:
            config_data = json.load(f)
    return config_data


config_data = _init()

host = config_data.get("host", "localhost")
webhost = config_data.get("webhost", host)
port = config_data.get("port", 5757)

# root of download directory (your collection)
initial_dir = pathlib.Path(
    os.getenv(
        "DDL_initial_dir",
        config_data.get("initial dir", "*** insert your path here ***"),
    )
)


saving_path: PathSpecification = PathSpecification(
    config_data.get("saving path", PathSpecification.COLLECTION)
)

# user API key here
key = os.getenv("DERPIBOORU_API_KEY", config_data.get("derpibooru API key", ""))
twibooru_key = os.getenv(
    "TWIBOORU_API_KEY", config_data.get("twibooru API key", "")
)
ponybooru_key = os.getenv(
    "PONYBOORU_API_KEY", config_data.get("ponybooru API key", "")
)
e621_login = os.getenv("E621_LOGIN", config_data.get("e621 login", None))
e621_API_KEY = os.getenv("E621_API_KEY", config_data.get("e621 API key", None))

# derpibooru-dl.py gui on/off
gui = config_data.get("enable gui", False)

# this option indicates to use file name from API or not
# affected on philomena based boorus
source_name_as_file_name = config_data.get("use API provided name", True)

max_name_length = config_data.get("max API provided name length", 128)

response_cache_dir = None

# TODO: what is this option for?
deleted_image_list_file_path = None

# indicates that file downloading should be manually started by user
manual_start = config_data.get("manual start", False)

simulate = False

db_user = os.getenv(
    "DDL_DB_USER", config_data.get("Application database user", None)
)
db_password = os.getenv(
    "DDL_DB_PASSWORD", config_data.get("Application database password", None)
)
app_db_host = os.getenv(
    "DDL_DB_HOST", config_data.get("Application database hostname", None)
)
app_db_prod = os.getenv(
    "DDL_DB_PROD", config_data.get("Production database name", None)
)
app_db_test = os.getenv(
    "DDL_DB_TEST", config_data.get("Testing database name", None)
)
derpibooru_dump_db_host = os.getenv(
    "DERPIBOORU_DUMP_HOST",
    config_data.get("Derpibooru database dump hostname", None),
)
derpibooru_dump_db_user = os.getenv(
    "DERPIBOORU_DUMP_USER",
    config_data.get("Derpibooru database dump username", db_user),
)
derpibooru_dump_db_password = os.getenv(
    "DERPIBOORU_DUMP_PASSWORD",
    config_data.get("password for derpibooru database dump", db_password),
)
