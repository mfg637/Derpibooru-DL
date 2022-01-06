#!/usr/bin/python3
# -*- coding: utf-8 -*- 
#tagResponse by mfg637

import pathlib

from config import initial_dir


def find_folder(parsed_tags: dict):
	output_directory = pathlib.Path(initial_dir)

	if 'my little pony' in parsed_tags['copyright']:
		output_directory = output_directory.joinpath("mlp")

	for mlp_generation_tag in {"g1", "g2", "g3", "g5"}:
		if mlp_generation_tag in parsed_tags['content']:
			output_directory.joinpath(mlp_generation_tag)
		
	# rules for /h/ folder
	if {'suggestive', 'questionable', 'explicit'} & parsed_tags['rating']:
		output_directory = output_directory.joinpath("h")

	# rules for characters
	if len(parsed_tags['original character']):
		output_directory = output_directory.joinpath("oc")
	elif 'cutie mark crusaders' in parsed_tags['content']:
		output_directory = output_directory.joinpath("cmc")
	elif 'shipping' in parsed_tags['content']:
		output_directory = output_directory.joinpath("shipping")
	elif len(parsed_tags['characters']) == 1:
		output_directory = output_directory.joinpath(list(parsed_tags['characters'])[0])
	elif "cinder glow" in parsed_tags['characters'] and\
		"summer flare" in parsed_tags['characters']:
		output_directory = output_directory.joinpath("cinder glow, summer flare")
	elif "bon bon" in parsed_tags['characters'] and\
		"sweetie drops" in parsed_tags['characters']:
		output_directory = output_directory.joinpath("bon bon, sweetie drops")
	elif "golden harvest" in parsed_tags['characters'] and\
		"carrot top" in parsed_tags['characters']:
		output_directory = output_directory.joinpath("carrot top, golden harvest")

	# rules for subfolders
	if 'my little pony: pony life' in parsed_tags['content']:
		output_directory = output_directory.joinpath("pony life")
	elif {'anthro', 'human'} & parsed_tags['species']:
		output_directory = output_directory.joinpath("antro")

	if {'questionable', 'explicit'} & parsed_tags['rating']:
		output_directory = output_directory.joinpath("c")
	elif {'horse'} & parsed_tags['species']:
		output_directory = output_directory.joinpath("horse")
	elif 'vector' in parsed_tags['content']:
		output_directory = output_directory.joinpath("vector")
	elif 'screencap' in parsed_tags['content']:
		output_directory = output_directory.joinpath("screencap")
	elif {'simple background', 'transparent background'} & parsed_tags['content']:
		output_directory = output_directory.joinpath("f")
	elif 'wallpaper' in parsed_tags['content']:
		output_directory = output_directory.joinpath("wallpaper")
	elif 'photo' in parsed_tags['content']:
		output_directory = output_directory.joinpath("photo")

	return str(output_directory)
