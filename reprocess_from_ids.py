#!/usr/bin/python3
# -*- coding: utf-8 -*-

import re
import pathlib
import logging
import argparse
import datetime
from time import sleep

import config
import parser
import medialib_service
from derpibooru_dl import download, logging as dl_logging

root_logger = logging.getLogger()
dl_logging.init(root_logger, "reprocess_ids")
logger = logging.getLogger(__name__)


ID_DETECTOR = re.compile(r"^([a-z]{2}\d+[$. _])")
ID_EXTRACTOR = re.compile(r"^([a-z]{2}\d+)")

prefixed_ids: set[str] = set()
prefix_representations: dict[str, list[pathlib.Path]] = {}
request_period = 100
cooldown_time = datetime.timedelta(minutes=5)


def collect_ids(folder_path: pathlib.Path):
    global prefixed_ids
    global prefix_representations

    abs_folder = folder_path.resolve()
    if not abs_folder.exists():
        return

    for file in abs_folder.iterdir():
        if file.name.startswith("."):
            continue
        if file.is_dir():
            collect_ids(file)
            continue

        match = ID_DETECTOR.match(file.name)
        if match:
            pid = ID_EXTRACTOR.match(file.name).group(1)
            if pid not in prefixed_ids:
                logger.debug(
                    f"Found new ID to reprocess: {pid} (from {file.name})"
                )
                prefixed_ids.add(pid)
                prefix_representations[pid] = []
            prefix_representations[pid].append(file)


def run_clean_download(prefixed_content_id: str):
    try:
        parsing_result = parser.parse_prefixed_id(prefixed_content_id)
        if parsing_result:
            origin_name, content_id = parsing_result
            if medialib_service.check_exists(origin_name, content_id):
                logger.info(
                    f"[{prefixed_content_id}] Already in medialib. Skipping download."
                )
                return True

        download(prefixed_content_id)
        logger.info(
            f"[{prefixed_content_id}] Successfully re-downloaded and imported."
        )
        return True

    except Exception as e:
        logger.error(f"[{prefixed_content_id}] Failed to reprocess: {e}")
        return False


def cleanup_garbage(pid: str):
    for file in prefix_representations[pid]:
        try:
            if file.is_file():
                file.unlink()
                logger.debug(f"Removed old representation: {file.name}")
        except Exception as e:
            logger.warning(f"Could not remove {file}: {e}")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Reprocess IDs from messy folders (prevent generation loss)"
    )
    arg_parser.add_argument(
        "dir", help="Folder with old/low-quality files", type=pathlib.Path
    )
    arg_parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove OLD files from source dir after success",
    )
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
        logger.error("Medialib is disabled.")
        exit(1)

    logger.info(f"Scanning {args.dir} for IDs...")
    collect_ids(args.dir)
    logger.info(f"Found {len(prefixed_ids)} unique IDs to re-process.")

    requests_remaining = request_period
    for pid in prefixed_ids:
        if requests_remaining == 0:
            logger.info(f"cooldown {cooldown_time}")
            sleep(cooldown_time.total_seconds())
            requests_remaining = request_period
        success = run_clean_download(pid)
        requests_remaining -= 1
        if success and args.cleanup:
            cleanup_garbage(pid)

    logger.info("Reprocessing finished.")
