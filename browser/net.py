#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.parse
import io
import random
import os
import sys
import pathlib

page = 1
items_per_page = 15
cache = dict()

if not os.path.isdir(os.path.join(os.path.dirname(sys.argv[0]),"browser", "tmpcache")):
    os.mkdir(os.path.join(os.path.dirname(sys.argv[0]),"browser", "tmpcache"))

def load_file(url, *args, **kwargs):
        filename = ""
        for x in range(16):
            filename += random.choice("qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM0123456789")
        req_t = urllib.request.urlopen(url, *args, **kwargs)
        try:
            cachefile = open(os.path.join(os.path.dirname(sys.argv[0]),"browser", "tmpcache", filename), 'bw')
        except FileNotFoundError:
            fpath = pathlib.PurePath(os.path.dirname(sys.argv[0]),"browser", "tmpcache", filename)
            print(fpath)
            cachefile = open(fpath, 'bw')
        cachefile.write(req_t.read())
        req_t.close()
        cachefile.close()
        cache.update([[url, os.path.join(os.path.dirname(sys.argv[0]),"browser", "tmpcache", filename)]])
        return filename


def CachedRequest(url, *args, **kwargs):
    if url not in cache or not os.path.exists(cache[url]):
        load_file(url, *args, **kwargs)
    return open(cache[url], 'br')


def clearCache():
    for url in cache:
        os.remove(cache[url])

def request_url(page_name, **kwargs):
    url = "https:{}".format(page_name)
    if url[-5:] != ".json":
        try:
            return cache[url]
        except KeyError as e:
            load_file(url)
            return cache[url]
    if kwargs:
        url += "?"
        url += urllib.parse.urlencode(kwargs)
    return url


def request(page_name, **kwargs):
    url = "https:{}".format(page_name)
    if url[-5:] != ".json":
        return CachedRequest(url)
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

