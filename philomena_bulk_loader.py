#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import time
import requests
import logging
from math import ceil

import config
import parser
import download_manager
import medialib_service
from derpibooru_dl import tagResponse, logging as dl_logging

root_logger = logging.getLogger()
dl_logging.init(root_logger, "philomena_bulk")
logger = logging.getLogger(__name__)


HOSTNAMES = {
    "derpibooru": parser.derpibooru.DerpibooruParser.get_domain_name_s(),
    "ponybooru": parser.ponybooru.PonybooruParser.get_domain_name_s(),
    "tantabus": parser.tantabus.TantabusAIParser.get_domain_name_s(),
    "furbooru": parser.furbooru.FurbooruParser.get_domain_name_s(),
}


PARSERS = {
    "derpibooru": parser.derpibooru.DerpibooruParser,
    "ponybooru": parser.ponybooru.PonybooruParser,
    "tantabus": parser.tantabus.TantabusAIParser,
    "furbooru": parser.furbooru.FurbooruParser,
}


site = "derpibooru"


def bulk_download(query, filter_id=None, limit=None):
    domain = HOSTNAMES[site]
    search_url = f"https://{domain}/api/v1/json/search/images"
    items_per_page = 50

    params = {
        "q": query,
        "per_page": items_per_page,
        "page": 1,
        "sf": "created_at",
        "sd": "desc",
    }

    if filter_id:
        params["filter_id"] = filter_id
    if config.key:
        params["key"] = config.key

    processed_count = 0
    current_page = 1
    total_pages = 1

    while current_page <= total_pages:
        logger.info(f"Fetching page {params['page']} for query: {query}")

        response = requests.get(search_url, params=params)
        if response.status_code != 200:
            logger.error(
                f"Search API error {response.status_code}: {response.text}"
            )
            break

        data = response.json()
        images = data.get("images", [])
        total = data.get("total", 0)
        total_pages = ceil(total / items_per_page)

        if not images:
            logger.info("No more images found.")
            break

        for img_data in images:
            if limit and processed_count >= limit:
                logger.info(f"Reached limit of {limit} images.")
                return

            image_id = img_data.get("id")
            image_url = f"https://{domain}/images/{image_id}"

            origin_name = site
            if medialib_service.check_exists(origin_name, str(image_id)):
                logger.info(f"Skipping {image_id}: already exists in medialib.")
                processed_count += 1
                continue

            wrapped_data = {"image": img_data}

            try:
                _parser = PARSERS[site](image_url, parsed_data=wrapped_data)

                process_single_parser(_parser, wrapped_data)
                processed_count += 1

            except Exception as e:
                logger.exception(f"Failed to process image {image_id}: {e}")

        if len(images) < params["per_page"]:
            break
        params["page"] += 1
        current_page += 1

        time.sleep(1)


def process_single_parser(_parser, data):
    parsed_tags: dict = _parser.tags_processing()
    logger.debug(f"Parsed tags: {parsed_tags}")

    outdir = tagResponse.find_folder(parsed_tags)
    logger.info(f"Output directory: {outdir}")

    dm = download_manager.make_download_manager(_parser)

    dm.download(outdir, data, parsed_tags)
    medialib_service.prepare_and_send_result(dm, parsed_tags, data, outdir)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Bulk download from Philomena-based booru"
    )
    arg_parser.add_argument("query", help="Search query (q parameter)")
    arg_parser.add_argument(
        "--filter-id", type=int, help="Optional Philomena filter ID"
    )
    arg_parser.add_argument(
        "--limit", type=int, help="Max images to download", default=None
    )
    arg_parser.add_argument(
        "--rewrite", action="store_true", help="Force rewrite existing files"
    )
    arg_parser.add_argument("--loglevel", default="INFO")
    arg_parser.add_argument(
        "-s",
        "--site",
        choices=["derpibooru", "ponybooru", "tantabus", "furbooru"],
        default="derpibooru",
    )

    args = arg_parser.parse_args()
    root_logger.setLevel(level=args.loglevel.upper())

    if args.rewrite:
        download_manager.download_manager.ENABLE_REWRITING = True

    if not config.use_medialib:
        logger.error("medialib is disabled in config.json")
        exit(1)

    site = args.site

    bulk_download(args.query, args.filter_id, args.limit)
