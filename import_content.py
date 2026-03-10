#!/usr/bin/python3
# -*- coding: utf-8 -*-

import re
import pathlib
import logging
import argparse

import config
import parser
import download_manager
import medialib_service
from derpibooru_dl import logging as dl_logging

root_logger = logging.getLogger()
dl_logging.init(root_logger, "sync_existing")
logger = logging.getLogger(__name__)

ID_EXTRACTOR = re.compile(r"^([a-z]{2}\d+)")


def process_folder(folder_path: pathlib.Path, remove_after: bool):
    logger.debug("start process_folder()")
    abs_folder = folder_path.resolve()

    if not abs_folder.exists() or not abs_folder.is_dir():
        logger.error(f"Path {folder_path} not found or not a directory.")
        return

    for file in abs_folder.iterdir():
        logger.debug(f"processing file {file}")
        if file.name.startswith("."):
            logger.info(f"skipped file {file}")
            continue
        elif file.is_dir():
            process_folder(file, remove_after)
            continue

        match = ID_EXTRACTOR.match(file.name)
        if not match:
            logger.warning(f"Skipped file (ID not found): {file.name}")
            continue

        prefixed_content_id = match.group(1)
        full_path = file.resolve()
        logger.info(f"Processing {file.name} (ID: {prefixed_content_id})...")

        parsing_result = parser.parse_prefixed_id(prefixed_content_id)
        if parsing_result is not None:
            origin_name, content_id = parsing_result
            is_found = medialib_service.check_exists(origin_name, content_id)
            if is_found:
                if remove_after:
                    logger.info(
                        f"Found content ({prefixed_content_id}), removing file {file}"
                    )
                    file.unlink()
                else:
                    logger.info(
                        f"Found content ({prefixed_content_id}), skipping"
                    )
                continue

        try:
            _parser = parser.get_parser(prefixed_content_id)

            try:
                data = _parser.get_data()
            except Exception as e:
                logger.error(
                    f"Unable to retrieve data for {prefixed_content_id}: {e}"
                )
                continue

            parsed_tags = _parser.tags_processing()
            dm = download_manager.make_download_manager(_parser)

            dm.skip_download = False

            medialib_service.prepare_for_import(
                dm=dm,
                parsed_tags=parsed_tags,
                file_path=full_path,
                remove_if_success=remove_after,
            )

            logger.info(f"Done processing: {prefixed_content_id}")

        except Exception as e:
            logger.exception(f"Processing error {file.name}: {e}")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Import exisitng files to the Medialib service"
    )
    arg_parser.add_argument("dir", help="Directory path", type=pathlib.Path)
    arg_parser.add_argument(
        "--remove",
        action="store_true",
        help="Удалять файл после успешного импорта",
    )
    arg_parser.add_argument(
        "-log",
        "--loglevel",
        default="INFO",
        help="Logging level (DEBUG, INFO, etc.)",
    )

    args = arg_parser.parse_args()
    root_logger.setLevel(level=args.loglevel.upper())

    if not config.use_medialib:
        logger.error(
            "Configuration issue: 'use_medialib' disabled in config.json."
        )
        exit(1)
    logger.debug(f"args.dir: {args.dir}")

    process_folder(args.dir, args.remove)
