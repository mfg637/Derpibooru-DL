#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import config
import os
import re
import urllib.request
import urllib.parse
import threading
import multiprocessing
if config.enable_images_optimisations:
    from . import imgOptimizer
    from PIL.Image import DecompressionBombError

downloader_thread = threading.Thread()
download_queue = []


if config.enable_images_optimisations:
    from . import imgOptimizer


def get_ID_by_URL(URL:str):
    return URL.split('?')[0].split('/')[-1]


def parseJSON(id:str, type="images"):
    url = 'https://derpibooru.org/api/v1/json/{}/{}'.format(type, urllib.parse.quote(id))
    print("parseJSON", url)
    urlstream=urllib.request.urlopen(url)
    rawdata=urlstream.read()
    urlstream.close()
    del urlstream
    data = json.loads(str(rawdata, 'utf-8'))
    while "duplicate_of" in data:
        data = parseJSON(str(data["duplicate_of"]))
    return data


def append2queue(**kwargs):
    global downloader_thread
    global download_queue
    download_queue.append(kwargs)
    if not downloader_thread.isAlive():
        downloader_thread = threading.Thread(target=async_downloader)
        downloader_thread.start()


def async_downloader():
    global download_queue
    while len(download_queue):
        current_download = download_queue.pop()
        pipe=multiprocessing.Pipe()
        params = current_download
        params['pipe'] = pipe[1]
        process = multiprocessing.Process(target=save_image, kwargs=params)
        process.start()
        imgOptimizer.sumos, imgOptimizer.sumsize, imgOptimizer.avq, imgOptimizer.items = pipe[0].recv()
        process.join()


def download_file(filename: str, src_url:str) -> None:
    urlstream = urllib.request.urlopen(src_url)
    file = open(filename, 'wb')
    file.write(urlstream.read())
    urlstream.close()
    file.close()


def in_memory_transcode(src_url, name, tags, output_directory, pipe):
    urlstream = urllib.request.urlopen(src_url)
    source = bytearray(urlstream.read())
    urlstream.close()
    transcoder = imgOptimizer.get_memory_transcoder(
        source, output_directory, name, tags, pipe
    )
    transcoder.transcode()


def save_image(output_directory: str, data: dict, tags: dict = None, pipe = None) -> None:
    if data['deletion_reason'] is not None:
        print('DELETED')
        if config.enable_images_optimisations and config.enable_multiprocessing:
            imgOptimizer.pipe_send(pipe)
        return
    if not os.path.isdir(output_directory):
        os.makedirs(output_directory)
    name = ''
    src_url = os.path.splitext(data['representations']['full'])[0]+'.'+data["format"].lower()
    if 'name' in data and data['name'] is not None:
        name = "{} {}".format(
            data["id"],
            re.sub('[/\[\]:;|=*".?]', '', os.path.splitext(data["name"])[0])
        )
    else:
        name = str(data["id"])
    src_filename = os.path.join(output_directory, "{}.{}".format(name, data["format"].lower()))

    print("filename", src_filename)
    print("image_url", src_url)

    if config.enable_images_optimisations:
        if data["format"] in {'png', 'jpg', 'jpeg', 'gif'}:
            if not os.path.isfile(src_filename) and not imgOptimizer.check_exists(src_filename, output_directory, name):
                try:
                    in_memory_transcode(src_url, name, tags, output_directory, pipe)
                except DecompressionBombError:
                    src_url = \
                        'https:' + os.path.splitext(data['representations']["large"])[0] + '.' + \
                        data["format"]
                    in_memory_transcode(src_url, name, tags, output_directory, pipe)
            elif not imgOptimizer.check_exists(src_filename, output_directory, name):
                transcoder = imgOptimizer.get_file_transcoder(
                    src_filename, output_directory, name, tags, pipe
                )
                transcoder.transcode()
            elif config.enable_multiprocessing:
                imgOptimizer.pipe_send(pipe)
        else:
            if not os.path.isfile(src_filename):
                download_file(src_filename, src_url)
            if config.enable_multiprocessing:
                imgOptimizer.pipe_send(pipe)
    else:
        if not os.path.isfile(src_filename):
            download_file(src_filename, src_url)
