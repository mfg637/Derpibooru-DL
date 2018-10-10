#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.parse

page = 1
items_per_page = 15


def request_url(page_name, **kwargs):
    url = "https:{}".format(page_name)
    if kwargs:
        url += "?"
        url += urllib.parse.urlencode(kwargs)
    return url


def request(page_name, **kwargs):
    url = "https:{}".format(page_name)
    if kwargs:
        url += "?"
        url += urllib.parse.urlencode(kwargs)
    return urllib.request.urlopen(url)


def parse_json(page_name, **kwargs):
    url = "//derpibooru.org/{}".format(page_name)
    connection = request(url, **kwargs)
    raw_data = connection.read()
    connection.close()
    return json.loads(str(raw_data, "utf-8"))


def get_page(search=None, **kwargs):
    if search is not None:
        page_data = parse_json("search.json", q=search, page=page, **kwargs)
    else:
        page_data = parse_json("images.json", page=page, **kwargs)
    if "images" in page_data:
        return page_data["images"]
    elif "search" in page_data:
        return page_data["search"]

