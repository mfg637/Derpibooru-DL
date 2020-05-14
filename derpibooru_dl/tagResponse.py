#!/usr/bin/python3
# -*- coding: utf-8 -*- 
#tagResponse by mfg637

import os
from derpibooru_dl import parser
from config import initial_dir
import mysql.connector

mysql_connection = mysql.connector.connect(
	host="localhost",
	user="derpibooru_dl_user",
	passwd="derpi_passwd",
	database="derpibooru_dl_app"
)

mysql_cursor = mysql_connection.cursor()


characters = set()

rating = set()

species = set()

content = set()


def tagIndex(taglist):
	artist=set()
	originalCharacter=set()
	indexed_characters = set()
	indexed_rating = set()
	indexed_species = set()
	indexed_content = set()
	for tag in taglist:
		if "oc:" in tag:
			originalCharacter.add(tag.split(':')[1])
		elif "artist:" in tag:
			artist.add(tag.split(':')[1])
		elif ":" in tag or '.' in tag or '-' in tag:
			continue
		else:
			query = "SELECT category FROM tag_categories WHERE tag=\"{}\";".format(tag)
			mysql_cursor.execute(query)
			result = mysql_cursor.fetchone()
			if result is None:
				category_name = ""
				indexed_tag = parser.parseJSON(tag, 'tags')['tag']
				if indexed_tag['category'] == "character":
					category_name = "character"
					indexed_characters.add(tag)
				elif indexed_tag['category'] == "rating":
					category_name = "rating"
					indexed_rating.add(tag)
				elif indexed_tag['category'] == "species":
					category_name = "species"
					indexed_species.add(tag)
				else:
					category_name = "content"
					indexed_content.add(tag)
				insert_query = "INSERT INTO tag_categories VALUES (\"{}\", \"{}\");".format(tag, category_name)
				mysql_cursor.execute(insert_query)
				mysql_connection.commit()
			else:
				if result[0]=="rating":
					indexed_rating.add(tag)
				elif result[0]=="character":
					indexed_characters.add(tag)
				elif result[0]=="species":
					indexed_species.add(tag)
				elif result[0]=="content":
					indexed_content.add(tag)
				else:
					print(result)
	return {'artist': artist, 'original character':originalCharacter,
		'characters': indexed_characters, 'rating': indexed_rating,
		'species': indexed_species, 'content': indexed_content}

def find_folder(parsed_tags:dict):
	outdir=initial_dir
	# rules for /h/ folder
	if {'suggestive', 'questionable', 'explicit'} & parsed_tags['rating']:
		outdir=os.path.join(outdir, 'h')

	if 'g1' in parsed_tags['content']:
		outdir=os.path.join(outdir, 'g1')
	elif 'g2' in parsed_tags['content']:
		outdir=os.path.join(outdir, 'g2')
	elif 'g3' in parsed_tags['content']:
		outdir=os.path.join(outdir, 'g3')
	# rules for characters
	if len(parsed_tags['original character']):
		outdir=os.path.join(outdir, 'oc')
	elif 'cutie mark crusaders' in parsed_tags['content']:
		outdir=os.path.join(outdir, 'cmc')
	elif 'shipping' in parsed_tags['content']:
		outdir=os.path.join(outdir, 'shipping')
	elif len(parsed_tags['characters'])==1:
		outdir=os.path.join(outdir, list(parsed_tags['characters'])[0])
	# rules for subfolders
	if {'questionable', 'explicit'} & parsed_tags['rating']:
		outdir=os.path.join(outdir, 'c')
	elif {'anthro', 'human'} & parsed_tags['species']:
		outdir=os.path.join(outdir, 'antro')
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