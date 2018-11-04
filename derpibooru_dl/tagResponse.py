#!/usr/bin/python3
# -*- coding: utf-8 -*- 
#tagResponse by mfg637

import os
from platform import system
from config import initial_dir

characters = set(
	[
		'applejack',
		'fluttershy',
		'twilight sparkle',
		'rainbow dash',
		'pinkie pie',
		'rarity',
		'derpy hooves',
		'lyra heartstrings',
		'zecora',
		'apple bloom',
		'sweetie belle',
		'scootaloo',
		'princess cadance',
		'princess celestia',
		'princess luna',
		'maud pie',
		'octavia',
		'gilda',
		'gabby',
		'princess flurry heart',
		'sunset shimmer',
		'starlight glimmer',
		'trixie',
		'coco pomel',
		'spitfire',
		'princess ember',
		'fleetfoot',
		'cutie mark crusaders',
		'spike',
		'moondancer',
		'dj pon3',
		'tempest shadow',
		'silverstream',
		'yona',
		'smolder',
		'gallus',
		'ocellus',
		'sandbar',
		'princess skystar',
		'limestone pie',
		'autumn blaze',
		'cozy glow',
		'arizona cow'
	]
)

art_category = set(['safe', 'suggestive', 'questionable', 'explicit', 'semi-grimdark', 'grimdark',
	'guro', 'shipping', 'portrait'])

art_type = set(
	[
		'traditional art',
		'digital art',
		'sketch',
		'vector',
		'simple background',
		'animated',
		'wallpaper',
		'screencap',
		'photo',
		'3d',
		'transparent background',
		'equestria girls'
	]
)

art_style = set(
	[
		'pony',
		'anthro',
		'humanisation',
		'horse',
		'hoers',
		'pegasus',
		'mare',
		'unicorn',
		'bipedal',
		'earth pony',
		'semi-anthro',
		'g1',
		'g2',
		'g3',
		'realistic anatomy'
	]
)

content = set(
	[
		'plot',
		'lided paper',
		'pencil drawing',
		'solo',
		'flying',
		'younger',
		'source filmmaker',
		'snow',
		'cuddling',
		'duo',
		'text',
		'wings',
		'magic',
		'prone',
		'looking at you',
		'socks',
		'bust',
		'lesbian',
		'bed',
		'selfie',
		'window',
		'sitting',
		'nudity',
		'looking at each other',
		'pillow',
		'fat',
		'blood',
		'diaper'
	]
)

def tagIndex(rawtags:str):
	taglist=rawtags.split(', ')
	artist=''
	originalCharacter=[]
	tagset=set()
	for tag in taglist:
		if ':' in set(tag):
			parsebuf=tag.split(':')
			if parsebuf[0]=='artist':
				artist=parsebuf[1]
			elif parsebuf[0]=='oc':
				originalCharacter.append(parsebuf[1])
		else:
			tagset.add(tag)
	indexed_characters=characters & tagset
	indexed_categories=art_category & tagset
	indexed_art_types=art_type & tagset
	indexed_art_styles=art_style & tagset
	indexed_content=content & tagset
	return {'artist': artist, 'original character':originalCharacter,
		'characters': indexed_characters, 'category': indexed_categories,
		'art_type': indexed_art_types, 'art_style': indexed_art_styles,
		'content': indexed_content}

def find_folder(parsed_tags:dict):
	outdir=initial_dir
	# rules for /h/ folder
	if set(['suggestive', 'questionable', 'explicit']) & parsed_tags['category']:
		outdir=os.path.join(outdir, 'h')
	# rules for characters
	if len(parsed_tags['original character']):
		outdir=os.path.join(outdir, 'oc')
	elif 'cutie mark crusaders' in parsed_tags['characters']:
		outdir=os.path.join(outdir, 'cmc')
	elif len(parsed_tags['characters'])==1:
		outdir=os.path.join(outdir, list(parsed_tags['characters'])[0])
	elif 'shipping' in parsed_tags['category']:
		outdir=os.path.join(outdir, 'shipping')
	# rules for subfolders
	if set(['questionable', 'explicit']) & parsed_tags['category']:
		outdir=os.path.join(outdir, 'c')
	elif set(['anthro', 'humanisation', 'semi-anthro']) & parsed_tags['art_style']:
		outdir=os.path.join(outdir, 'antro')
	elif set(['horse', 'hoers', 'realistic anatomy']) & parsed_tags['art_style']:
		outdir=os.path.join(outdir, 'horse')
	elif 'vector' in parsed_tags['art_type']:
		outdir=os.path.join(outdir, 'vector')
	elif 'screencap' in parsed_tags['art_type']:
		outdir=os.path.join(outdir, 'screencap')
	elif set(['simple background', 'transparent background']) & parsed_tags['art_type']:
		outdir=os.path.join(outdir, 'f')
	elif 'wallpaper' in parsed_tags['art_type']:
		outdir=os.path.join(outdir, 'wallpaper')
	elif 'photo' in parsed_tags['art_type']:
		outdir=os.path.join(outdir, 'photo')
	elif 'g1' in parsed_tags['art_style']:
		outdir=os.path.join(outdir, 'g1')
	elif 'g2' in parsed_tags['art_style']:
		outdir=os.path.join(outdir, 'g2')
	elif 'g3' in parsed_tags['art_style']:
		outdir=os.path.join(outdir, 'g3')
	return outdir