#!/usr/bin/python3
# -*- coding: utf-8 -*- 
#tagResponse by mfg637

import os
from config import initial_dir


def find_folder(parsed_tags:dict):
	outdir=initial_dir
	if 'g1' in parsed_tags['content']:
		outdir=os.path.join(outdir, 'g1')
	elif 'g2' in parsed_tags['content']:
		outdir=os.path.join(outdir, 'g2')
	elif 'g3' in parsed_tags['content']:
		outdir=os.path.join(outdir, 'g3')
	elif 'g5' in parsed_tags['content']:
		outdir = os.path.join(outdir, 'g5')
		
	# rules for /h/ folder
	if {'suggestive', 'questionable', 'explicit'} & parsed_tags['rating']:
		outdir=os.path.join(outdir, 'h')
	# rules for characters
	if len(parsed_tags['original character']):
		outdir=os.path.join(outdir, 'oc')
	elif 'cutie mark crusaders' in parsed_tags['content']:
		outdir=os.path.join(outdir, 'cmc')
	elif 'shipping' in parsed_tags['content']:
		outdir=os.path.join(outdir, 'shipping')
	elif len(parsed_tags['characters'])==1:
		outdir=os.path.join(outdir, list(parsed_tags['characters'])[0])
	elif "cinder glow" in parsed_tags['characters'] and\
		"summer flare" in parsed_tags['characters']:
		outdir = os.path.join(outdir, "cinder glow, summer flare")
	elif "bon bon" in parsed_tags['characters'] and\
		"sweetie drops" in parsed_tags['characters']:
		outdir = os.path.join(outdir, "bon bon, sweetie drops")
	elif "golden harvest" in parsed_tags['characters'] and\
		"carrot top" in parsed_tags['characters']:
		outdir = os.path.join(outdir, "carrot top, golden harvest")
	# rules for subfolders
	if 'my little pony: pony life' in parsed_tags['content']:
		outdir=os.path.join(outdir, "pony life")
	elif {'anthro', 'human'} & parsed_tags['species']:
		outdir=os.path.join(outdir, 'antro')

	if {'questionable', 'explicit'} & parsed_tags['rating']:
		outdir=os.path.join(outdir, 'c')
	elif {'horse'} & parsed_tags['species']:
		outdir=os.path.join(outdir, 'horse')
	elif 'vector' in parsed_tags['content']:
		outdir=os.path.join(outdir, 'vector')
	elif 'screencap' in parsed_tags['content']:
		outdir=os.path.join(outdir, 'screencap')
	elif {'simple background', 'transparent background'} & parsed_tags['content']:
		outdir=os.path.join(outdir, 'f')
	elif 'wallpaper' in parsed_tags['content']:
		outdir=os.path.join(outdir, 'wallpaper')
	elif 'photo' in parsed_tags['content']:
		outdir=os.path.join(outdir, 'photo')
	return outdir