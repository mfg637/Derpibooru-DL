#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys, json

import math

import requests

import parser

try:
    import config
except ImportError as e:
    print('error importing config.py')
    raise(e)


items_per_page = 15
pages = 1
current_page = 1

search_query = ""
if len(sys.argv) == 2:
    search_query = sys.argv[1]
else:
    print("search query is empty", file=sys.stderr)
    exit(1)

pages = 1


# first line (header) of CSV file
print("character", "faves", "score", "\"uploaded at\"")


while current_page<=pages:
    print('loading page {} of {}'.format(current_page, pages), file=sys.stderr)
    request={
        'search_query': search_query,
        'page': current_page,
        'perpage': items_per_page
    }
    request_url = (("https://derpibooru.org/api/v1/json/search/images?"
                    "q={search_query}"
                    "&page={page}&perpage={perpage}")).format(**request)
    if len(config.key) != 0:
        request_url += "&key={}".format(config.key)
    print("request url:", request_url, file=sys.stderr)
    try:
        request_data = requests.get(request_url)
    except Exception as e:
        print(e, file=sys.stderr)
        continue
    data = None
    try:
        data = request_data.json()
    except json.JSONDecodeError as e:
        print("JSON decode error. HTTP status code:{} Raw data: {}".format(
            request_data.status_code, request_data.text), file=sys.stderr)
        raise e
    for image in data['images']:
        _parser = parser.derpibooru.DerpibooruParser(None, {"image": image})
        if config.use_medialib_db:
            _parser.set_tags_indexer(parser.tag_indexer.MedialibTagIndexer(_parser))
        else:
            _parser.set_tags_indexer(parser.tag_indexer.DefaultTagIndexer(_parser))
        parsed_tags = _parser.tagIndex()
        print(
            "\""+parsed_tags['characters'].pop()+"\"" if len(parsed_tags['characters']) > 0 else "",
            image['faves'],
            image['score'],
            "\""+image['created_at']+"\""
        )

    pages = math.ceil(data['total'] / items_per_page)
    current_page += 1
