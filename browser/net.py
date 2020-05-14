#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.parse
import random
import os
import sys
import config

page = 1
items_per_page = 15
cache = dict()
app_dir = os.path.realpath(os.path.dirname(sys.argv[0]))

if config.browser_tmpcache_directory is None and not os.path.isdir(os.path.join(app_dir,"browser", "tmpcache")):
    os.mkdir(os.path.join(app_dir,"browser", "tmpcache"))

def load_file(url, *args, **kwargs):
        global cache
        filename = ""
        for x in range(16):
            filename += random.choice("qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM0123456789")
        req_t = urllib.request.urlopen(url, *args, **kwargs)
        cache_filename = ''
        if config.browser_tmpcache_directory is None:
            cache_filename = os.path.join(app_dir,"browser", "tmpcache", filename)
        else:
            cache_filename = os.path.join(config.browser_tmpcache_directory, filename)
        cachefile = open(cache_filename, 'bw')
        cachefile.write(req_t.read())
        req_t.close()
        cachefile.close()
        cache.update([[url, cache_filename]])
        return filename


def CachedRequest(url, *args, **kwargs):
    if url not in cache or not os.path.exists(cache[url]):
        load_file(url, *args, **kwargs)
    return open(cache[url], 'br')


def clearCache():
    for url in cache:
        os.remove(cache[url])

def request_url(page_name, **kwargs):
    url = "{}".format(page_name)
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


def request(page_name, json=False,  **kwargs):
    url = "{}".format(page_name)
    if not json:
        return CachedRequest(url)
    if kwargs:
        url += "?"
        url += urllib.parse.urlencode(kwargs)
    return urllib.request.urlopen(url)


def parse_json(page_name, **kwargs):
    url = "https://derpibooru.org/{}".format(page_name)
    connection = request(url, True, **kwargs)
    raw_data = connection.read()
    connection.close()
    return json.loads(str(raw_data, "utf-8"))
