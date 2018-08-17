#!/usr/bin/python3
# -*- coding: utf-8 -*-

import urllib.request, json, os, re
import config

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

def download(outdir, data, tags=None):
	if 'file_name' in data and data['file_name'] is not None:
		filename=os.path.join(outdir, "{} {}.{}".format(data["id"],
			re.sub('[/\[\]:;|=*".?]', '', os.path.splitext(data["file_name"])[0]),
			data["original_format"]))
	else:
		filename=os.path.join(outdir, "{}.{}".format(data["id"],
			data["original_format"]))
	if config.enable_images_optimisations and \
		data["original_format"] in set(['png', 'jpg', 'jpeg', 'gif']):
		if not os.path.isfile(filename) and \
			not os.path.isfile(os.path.join(outdir, "{} {}.{}".format(
				data["id"],
				re.sub('[/\[\]:;|=*".?]', '', os.path.splitext(data["file_name"])[0]),
				imgOptimizer.getExt[data["original_format"]]
		))):
			print(filename)
			print('https:'+os.path.splitext(data['image'])[0]+'.'+data["original_format"])
			urlstream=urllib.request.urlopen(
				'https:'+os.path.splitext(data['image'])[0]+'.'+data["original_format"]
				)
			file = open(filename, 'wb')
			file.write(urlstream.read())
			urlstream.close()
			file.close()
		if not os.path.isfile(os.path.join(outdir, "{} {}.{}".format(
				data["id"],
				re.sub('[/\[\]:;|=*".?]', '', os.path.splitext(data["file_name"])[0]),
				imgOptimizer.getExt[data["original_format"]]
		))):
			imgOptimizer.transcode(
				filename,
				outdir,
				"{} {}".format(
					data["id"],
					re.sub('[/\[\]:;|=*".?]', '', os.path.splitext(data["file_name"])[0])
				),
				tags
			)
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