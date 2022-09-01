#!/usr/bin/python3
# -*- coding: utf-8 -*-

import multiprocessing
import random

import requests
import os
import json
import logging
import argparse

import math

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

logging.basicConfig(level=logging.INFO, format="%(process)dx%(thread)d::%(levelname)s::%(name)s::%(message)s")

logger = logging.getLogger(__name__)

error_str1 = 'Error: user API key required.'
error_str1_continue = 'Find you API key in page: "https://derpibooru.org/pages/api"'

tasks = []

try:
    if len(config.key) == 0:
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
argument_parser.add_argument("n value", type=int, help="numeric value of some period type", default=3)
argument_parser.add_argument("period", type=str, help="type of period", default="days")
argument_parser.add_argument("--items-per-page", type=int, default=15)
argument_parser.add_argument("--rewrite", help="force to rewrite existing files", action="store_true")
args = argument_parser.parse_args()

n_value = vars(args)['n value']
period = args.period
items_per_page = args.items_per_page
download_manager.download_manager.ENABLE_REWRITING = args.rewrite
if period == "pages":
    pages = n_value

try:
    while current_page <= pages:
        print('loading page {} of {}'.format(current_page, pages))
        request = {
            'nvalue': n_value,
            'period': period,
            'page': current_page,
            'key': config.key,
            'perpage': items_per_page
        }
        request_url = None
        if period == "pages":
            request_url = ("https://derpibooru.org/api/v1/json/search/images?"
                           "q=my%3Aupvotes&key={key}"
                           "&page={page}&perpage={perpage}").format(**request)
        else:
            request_url = ("https://derpibooru.org/api/v1/json/search/images?"
                           "q=first_seen_at.gt%3A{nvalue}+{period}+ago+"
                           "%26%26+my%3Aupvotes&key={key}"
                           "&page={page}&perpage={perpage}").format(**request)
        print("request url:", request_url)
        request_data = requests.get(request_url)
        data = None
        if request_data.status_code == 404:
            raise IndexError("not founded \"{}\"".format(request_url))
        try:
            data = request_data.json()
        except json.JSONDecodeError as e:
            print("JSON decode error. HTTP status code:{} Raw data: {}".format(
                request_data.status_code, request_data.text))
            raise e

        if current_page == 1 and period != "pages":
            pages = int(math.ceil(data['total'] / items_per_page))
        for item in data['images']:
            _parser = parser.derpibooru.DerpibooruParser(None, {"image": item})
            if config.use_medialib_db:
                _parser = parser.tag_indexer.MedialibTagIndexer(_parser, None)
            else:
                _parser = parser.tag_indexer.DefaultTagIndexer(_parser, None)
            parsed_tags = _parser.tagIndex()
            outdir = tagResponse.find_folder(parsed_tags)
            dm = download_manager.make_download_manager(_parser)
            if not os.path.isdir(outdir):
                os.makedirs(outdir)
            tasks.append((dm, outdir, {"image": item}, parsed_tags))
        current_page += 1

    db_lock = multiprocessing.Lock()
    dl_pool = multiprocessing.Pool(
        processes=config.workers, initializer=medialib_db.common.db_lock_init, initargs=(db_lock,)
    )
    random.shuffle(tasks)
    logger.info("processing {} requests".format(len(tasks)))
    results = dl_pool.map(download_manager.save_call, tasks, chunksize=1)
    pyimglib.transcoding.statistics.update_stats(results)
except Exception as e:
    raise e
finally:
    if config.do_transcode:
        pyimglib.transcoding.statistics.log_stats()
