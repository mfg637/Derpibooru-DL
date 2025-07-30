#!/usr/bin/python3
# -*- coding: utf-8 -*-

import multiprocessing

import requests
import os
import json
import logging
import argparse

import download_manager
import medialib_db
import pyimglib
from derpibooru_dl import tagResponse
import parser

try:
    import config
except ImportError as e:
    print('error importing config.py')
    raise e

logging.basicConfig(
    level=logging.INFO,
    format="%(process)dx%(thread)d::%(levelname)s::%(name)s::%(message)s"
)

logger = logging.getLogger(__name__)

error_str1 = 'Error: user API key required.'
error_str1_continue = \
    'Find you API key in page: "https://derpibooru.org/pages/api"'

tasks = []

try:
    if len(config.e621_API_KEY) == 0:
        print(error_str1)
        exit()
except AttributeError:
    print(error_str1)
    print('Add string "key = \'you API key here\'" in "config.py" file.')
    print(error_str1_continue)
    exit()

pages = 1
current_page = 1


argument_parser = argparse.ArgumentParser()
argument_parser.add_argument("pool_id", type=int)
argument_parser.add_argument(
    "--rewrite", help="force to rewrite existing files", action="store_true"
)
args = argument_parser.parse_args()

pool_id = vars(args)['pool_id']
download_manager.download_manager.ENABLE_REWRITING = args.rewrite

medialib_db_connection = medialib_db.common.make_connection()

album_artist = None
pool_title = None
album_id = None

album_order_dict: dict[int, int] = dict()

try:
    request_url = (
        "https://e621.net/pools/{}.json?login={}&api_key={}"
    ).format(
        pool_id, config.e621_login, config.e621_API_KEY
    )
    headers = {
        'User-Agent': (
            'e621_pool_downloader.py (by mfg637) '
            '(https://github.com/mfg637/Derpibooru-DL)'
        )
    }
    print("request url:", request_url)
    request_data = requests.get(request_url, headers=headers)
    pool_data = None
    if request_data.status_code == 404:
        raise IndexError("not founded \"{}\"".format(request_url))
    try:
        pool_data = request_data.json()
    except json.JSONDecodeError as e:
        print("JSON decode error. HTTP status code:{} Raw data: {}".format(
            request_data.status_code, request_data.text))
        raise e

    pool_title: str = pool_data['name'].replace("_", " ")
    print("Pool title is {}".format(pool_title))

    for album_order, origin_content_id in enumerate(pool_data['post_ids']):
        _parser = parser.e621.E621Parser(str(origin_content_id))
        if config.use_medialib_db:
            _parser = parser.tag_indexer.MedialibTagIndexer(_parser, None)
        else:
            _parser = parser.tag_indexer.DefaultTagIndexer(_parser, None)
        data = _parser.parseJSON()
        logger.info(
            "Request for download: {}{}".format(
                _parser.get_filename_prefix(),
                _parser.getID()
            )
        )
        parsed_tags = _parser.tagIndex()
        if album_artist is None:
            album_artist = parsed_tags["artist"].copy().pop()

        set_id = medialib_db.tags_indexer.check_tag_exists(
            pool_title, 'set', medialib_db_connection
        )
        if set_id is None:
            set_id = medialib_db.tags_indexer.insert_new_tag(
                pool_title,
                'set',
                "set: {}".format(pool_title),
                medialib_db_connection
            )

        artist_id = medialib_db.tags_indexer.check_tag_exists(
            album_artist, 'artist', medialib_db_connection
        )
        if artist_id is None:
            artist_id = medialib_db.tags_indexer.insert_new_tag(
                album_artist,
                'artist',
                "artist:{}".format(pool_title),
                medialib_db_connection
            )

        album_id = medialib_db.album.get_album_id(
            set_id, artist_id, medialib_db_connection
        )
        if album_id is None:
            album_id = medialib_db.album.make_album(
                set_id, artist_id, medialib_db_connection
            )

        content_info = medialib_db.find_content_from_source(
            _parser.get_origin_name(), _parser.getID(), medialib_db_connection
        )

        if content_info is not None:
            content_id = content_info[0]
            medialib_db.add_tags_for_content_by_tag_ids(
                content_id, [set_id,], medialib_db_connection
            )
            medialib_db.album.set_album_order(
                album_id, content_id, album_order, medialib_db_connection
            )
            medialib_db_connection.commit()
            continue
        else:
            album_order_dict[origin_content_id] = album_order

        outdir = tagResponse.find_folder(parsed_tags)
        dm = download_manager.make_download_manager(_parser)
        if not os.path.isdir(outdir):
            os.makedirs(outdir)
        tasks.append((dm, outdir, data, parsed_tags))

    db_lock = multiprocessing.Lock()
    dl_pool = download_manager.DownloadManager.create_pool(config.workers)
    logger.info("processing {} requests".format(len(tasks)))
    results = dl_pool.map(download_manager.save_call, tasks, chunksize=1)
    pyimglib.transcoding.statistics.update_stats(results)
except Exception as e:
    raise e
finally:
    if config.do_transcode:
        pyimglib.transcoding.statistics.log_stats()

print("registering downloaded content")

for origin_content_id in album_order_dict:
    content_info = medialib_db.find_content_from_source(
        'e621', str(origin_content_id), medialib_db_connection
    )

    content_id = content_info[0]
    medialib_db.album.set_album_order(
        album_id,
        content_id,
        album_order_dict[origin_content_id],
        medialib_db_connection
    )

    medialib_db_connection.commit()

medialib_db_connection.close()
