#!/usr/bin/python3
# -*- coding: utf-8 -*- 
#tagResponse by mfg637

import pathlib

import config

import datetime
import abc


class FilesystemDirectoryManager(abc.ABC):
	@abc.abstractmethod
	def choose_folder(self, tags: dict[str, set]) -> pathlib.Path:
		pass


class TagBasedDirectory(FilesystemDirectoryManager):

	def choose_folder(self, tags: dict[str, set]) -> pathlib.Path:
		output_directory = pathlib.Path(config.initial_dir)

		if 'my little pony' in tags['copyright']:
			output_directory = output_directory.joinpath("mlp")
		elif "gryphon" in tags["species"]:
			output_directory = output_directory.joinpath("g6")
		elif "horse" in tags["species"]:
			output_directory = output_directory.joinpath("horses")

		for mlp_generation_tag in {"g1", "g2", "g3", "g5"}:
			if mlp_generation_tag in tags['content']:
				output_directory.joinpath(mlp_generation_tag)

		# rules for /h/ folder
		if {'suggestive', 'questionable', 'explicit'} & tags['rating']:
			output_directory = output_directory.joinpath("h")

		# rules for characters
		if len(tags['original character']):
			output_directory = output_directory.joinpath("oc")
		elif 'cutie mark crusaders' in tags['content']:
			output_directory = output_directory.joinpath("cmc")
		elif 'shipping' in tags['content']:
			output_directory = output_directory.joinpath("shipping")
		elif len(tags['characters']) == 1:
			output_directory = output_directory.joinpath(list(tags['characters'])[0])
		elif "cinder glow" in tags['characters'] and \
				"summer flare" in tags['characters']:
			output_directory = output_directory.joinpath("cinder glow, summer flare")
		elif "bon bon" in tags['characters'] and \
				"sweetie drops" in tags['characters']:
			output_directory = output_directory.joinpath("bon bon, sweetie drops")
		elif "golden harvest" in tags['characters'] and \
				"carrot top" in tags['characters']:
			output_directory = output_directory.joinpath("carrot top, golden harvest")

		# rules for subfolders
		if 'my little pony: pony life' in tags['content']:
			output_directory = output_directory.joinpath("pony life")
		elif {'anthro', 'human'} & tags['species']:
			output_directory = output_directory.joinpath("antro")

		if {'questionable', 'explicit'} & tags['rating']:
			output_directory = output_directory.joinpath("c")
		elif 'horse' in tags['species'] and 'my little pony' not in tags['copyright']:
			output_directory = output_directory.joinpath("horse")
		elif 'vector' in tags['content']:
			output_directory = output_directory.joinpath("vector")
		elif 'screencap' in tags['content']:
			output_directory = output_directory.joinpath("screencap")
		elif {'simple background', 'transparent background'} & tags['content']:
			output_directory = output_directory.joinpath("f")
		elif 'wallpaper' in tags['content']:
			output_directory = output_directory.joinpath("wallpaper")
		elif 'photo' in tags['content']:
			output_directory = output_directory.joinpath("photo")

		return output_directory


class DateBasedDirectory(FilesystemDirectoryManager):

	def choose_folder(self, tags: dict[str, set]) -> pathlib.Path:
		output_directory = pathlib.Path(config.medialib_directory)

		current_date = datetime.datetime.now()

		return output_directory.joinpath(str(current_date.year), str(current_date.month), str(current_date.day))


def find_folder(parsed_tags: dict[str, set]):
	dir_manager: FilesystemDirectoryManager | None = None

	if config.saving_path == config.SavingPath.COLLECTION:
		dir_manager = TagBasedDirectory()
	elif config.saving_path == config.SavingPath.MEDIALIB:
		dir_manager = DateBasedDirectory()

	if dir_manager is None:
		raise ValueError("unexpected value of config.saving_path: {}".format(config.saving_path))

	return dir_manager.choose_folder(parsed_tags)
