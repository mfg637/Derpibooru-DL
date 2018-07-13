#!/usr/bin/python3
# -*- coding: utf-8 -*-

import urllib.request, os, sys, json
import tkinter
from tkinter import filedialog
from derpibooru_dl import tagResponse, parser

if len(sys.argv)==1:
	from derpibooru_dl import gui
	GUI = gui.GUI()

#id=sys.argv[1].split('?')[0].split('/')[3]
id_list=[parser.get_ID_by_URL(elem) for elem in sys.argv[1:]]

for id in id_list:
	print('open connection')

	data=parser.parseJSON(id)

	parsed_tags=tagResponse.tagIndex(data['tags'])
	print(parsed_tags)
	outdir=tagResponse.find_folder(parsed_tags)
	print(outdir)

	if not os.path.isdir(outdir):
		os.makedirs(outdir)

	parser.download(outdir, data)