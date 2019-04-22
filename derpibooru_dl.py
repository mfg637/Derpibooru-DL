#!/usr/bin/python3
# -*- coding: utf-8 -*-

import urllib.request, os, sys, json
import tkinter
from tkinter import filedialog
from derpibooru_dl import tagResponse, parser
import config
if config.enable_images_optimisations:
	from derpibooru_dl import imgOptimizer

if len(sys.argv)==1:
	from derpibooru_dl import gui
	GUI = gui.GUI()

#id=sys.argv[1].split('?')[0].split('/')[3]
id_list=[parser.get_ID_by_URL(elem) for elem in sys.argv[1:]]

for id in id_list:
	print('open connection')

	data=parser.parseJSON(id)

	parsed_tags=tagResponse.tagIndex(data['tags'])
	print("parsed tags", parsed_tags)
	outdir=tagResponse.find_folder(parsed_tags)
	print("outdir", outdir)

	if not os.path.isdir(outdir):
		os.makedirs(outdir)

	parser.save_image(outdir, data, parsed_tags)

if config.enable_images_optimisations:
	imgOptimizer.printStats()