#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import config
import os
import re
import urllib.request
import threading

downloader_thread = threading.Thread()
download_queue = []


if config.enable_images_optimisations:
	from . import imgOptimizer


def get_ID_by_URL(URL:str):
	return URL.split('?')[0].split('/')[-1]


def parseJSON(id:str):
	print('https://derpibooru.org/'+id+'.json')
	urlstream=urllib.request.urlopen('https://derpibooru.org/'+id+'.json')
	rawdata=urlstream.read()
	urlstream.close()
	del urlstream
	return json.loads(str(rawdata, 'utf-8'))


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
		download(**current_download)


def download(outdir, data, tags=None, pipe=None):
	if not os.path.isdir(outdir):
		os.makedirs(outdir)
	if 'file_name' in data and data['file_name'] is not None:
		filename=os.path.join(outdir, "{} {}.{}".format(data["id"],
			re.sub('[/\[\]:;|=*".?]', '', os.path.splitext(data["file_name"])[0]),
			data["original_format"]))
	else:
		filename=os.path.join(outdir, "{}.{}".format(data["id"],
			data["original_format"]))
	if config.enable_images_optimisations and \
		data["original_format"] in set(['png', 'jpg', 'jpeg', 'gif']):
		if not os.path.isfile(filename) and (
				('file_name' in data and data['file_name'] is not None and \
					(not os.path.isfile(os.path.join(outdir, "{} {}.{}".format(
						data["id"],
						re.sub('[/\[\]:;|=*".?]', '', os.path.splitext(data["file_name"])[0]),
						imgOptimizer.getExt[data["original_format"]])))
				))
				or (not os.path.isfile(os.path.join(outdir, "{}.{}".format(
					data["id"], imgOptimizer.getExt[data["original_format"]]))))
			):
			print(filename)
			print('https:'+os.path.splitext(data['image'])[0]+'.'+data["original_format"])
			urlstream=urllib.request.urlopen(
				'https:'+os.path.splitext(data['image'])[0]+'.'+data["original_format"]
				)
			file = open(filename, 'wb')
			file.write(urlstream.read())
			urlstream.close()
			file.close()
		if ('file_name' in data and data['file_name'] is not None) and \
				(not os.path.isfile(os.path.join(outdir, "{} {}.{}".format(
				data["id"],
				re.sub('[/\[\]:;|=*".?]', '', os.path.splitext(data["file_name"])[0]),
				imgOptimizer.getExt[data["original_format"]])))):
			imgOptimizer.transcode(
				filename,
				outdir,
				"{} {}".format(
					data["id"],
					re.sub('[/\[\]:;|=*".?]', '', os.path.splitext(data["file_name"])[0])
				),
				tags,
				pipe
			)
		elif not os.path.isfile(os.path.join(outdir, "{}.{}".format(
				data["id"],
				imgOptimizer.getExt[data["original_format"]]))):
			imgOptimizer.transcode(
				filename,
				outdir,
				str(data["id"]),
				tags,
				pipe
			)
		elif pipe is not None:
			pipe.send((0,0,0,0))
			pipe.close()
	else:
		if not os.path.isfile(filename):
			print(filename)
			print('https:'+os.path.splitext(data['image'])[0]+'.'+data["original_format"])
			urlstream=urllib.request.urlopen(
				'https:'+os.path.splitext(data['image'])[0]+'.'+data["original_format"]
				)
			file = open(filename, 'wb')
			file.write(urlstream.read())
			urlstream.close()
			file.close()