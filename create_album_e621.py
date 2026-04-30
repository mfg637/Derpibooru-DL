#!/usr/bin/python3
# -*- coding: utf-8 -*-

import requests
import logging
import argparse
import datetime
from time import sleep
import config
import medialib_service
from derpibooru_dl import download, logging as dl_logging
import parser

root_logger = logging.getLogger()
dl_logging.init(root_logger, "e621_album_creator")
logger = logging.getLogger(__name__)

request_period = 100
cooldown_time = datetime.timedelta(minutes=5)


def register_album(origin_name: str, album_title: str, post_ids: list[int]):
    url = f"http://{config.ml_host}:{config.ml_port}/media_receiving/api/album/register/"
    payload = {
        "origin_name": origin_name,
        "album_title": album_title,
        "content_sequence": [str(pid) for pid in post_ids],
        "ordered_content": None,
    }

    logger.info(
        f"Registering album '{album_title}' with {len(post_ids)} posts..."
    )
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logger.info("Album successfully registered.")
            return True
        else:
            logger.error(
                f"Failed to register album. Server returned {response.status_code}: {response.text}"
            )
            return False
    except Exception as e:
        logger.exception(f"Error sending request to register album: {e}")
        return False


def process_pool(pool_id: int):
    pools_parser = parser.e621.E621Parser(pool_id)
    pool_data = pools_parser.parseJSON(pool_id, "pools")

    pool_id_response = pool_data.get("id")
    pool_name = pool_data.get("name", f"Pool {pool_id}").replace("_", " ")
    post_ids = pool_data.get("post_ids", [])

    if not post_ids:
        logger.warning(f"No post IDs found in pool {pool_id_response}.")
        return

    logger.info(f"Processing e621 pool: {pool_name} (ID: {pool_id_response})")

    new_downloads_triggered = False
    requests_remaining = request_period

    for post_id in post_ids:
        str_post_id = str(post_id)

        if medialib_service.check_exists("e621", str_post_id):
            logger.debug(f"Post e621:{str_post_id} already exists.")
            continue

        logger.info(
            f"Post e621:{str_post_id} not found. Triggering download..."
        )
        if requests_remaining == 0:
            logger.info(f"cooldown {cooldown_time}")
            sleep(cooldown_time.total_seconds())
            requests_remaining = request_period
        download(f"ef{str_post_id}")
        requests_remaining -= 1
        new_downloads_triggered = True

    if new_downloads_triggered:
        print("\n" + "=" * 50)
        print("Warning: new tasks was created im medialib service.")
        input("press Enter, when processing is done")
        print("=" * 50 + "\n")

    register_album(origin_name="e621", album_title=pool_name, post_ids=post_ids)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Create album from e621 pool ID"
    )
    arg_parser.add_argument("pool_id", help="e621 pool ID", type=int)
    arg_parser.add_argument(
        "--request-period",
        type=int,
        default=100,
        help="max request count before cooldown",
    )
    arg_parser.add_argument("-log", "--loglevel", default="INFO")

    args = arg_parser.parse_args()
    root_logger.setLevel(level=args.loglevel.upper())
    request_period = max(1, min(args.request_period, 1000))

    if not config.use_medialib:
        logger.error("medialib is disabled in config.json")
        exit(1)

    process_pool(args.pool_id)
