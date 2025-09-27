#!/usr/bin/python3
# -*- coding: utf-8 -*-
# tagResponse by mfg637

import pathlib

import config

import datetime
import abc

import database


tag_categories = database.tag.TagCategory


class FilesystemDirectoryManager(abc.ABC):
    @abc.abstractmethod
    def choose_folder(self, tags: dict[str, set]) -> pathlib.Path:
        pass


class TagBasedDirectory(FilesystemDirectoryManager):

    def choose_folder(self, tags: dict[str, set]) -> pathlib.Path:
        output_directory = pathlib.Path(config.initial_dir)

        if "copyright" in tags and "my little pony" in tags["copyright"]:
            output_directory = output_directory.joinpath("mlp")
        elif "species" in tags:
            if "gryphon" in tags["species"]:
                output_directory = output_directory.joinpath("g6")
            elif "horse" in tags["species"]:
                output_directory = output_directory.joinpath("horses")

        for mlp_generation_tag in {"g1", "g2", "g3", "g5"}:
            if mlp_generation_tag in tags[tag_categories.COPYRIGHT]:
                output_directory.joinpath(mlp_generation_tag)

        # rules for characters
        if tag_categories.CHARACTER in tags:
            if "oc only" in tags[tag_categories.CHARACTER]:
                output_directory = output_directory.joinpath("oc")
            elif (
                tag_categories.CHARACTER_GROUP in tags
                and "cutie mark crusaders"
                in tags[tag_categories.CHARACTER_GROUP]
            ):
                output_directory = output_directory.joinpath("cmc")
            elif "content" in tags and "shipping" in tags["content"]:
                output_directory = output_directory.joinpath("shipping")
            elif len(tags[tag_categories.CHARACTER]) == 1:
                output_directory = output_directory.joinpath(
                    list(tags[tag_categories.CHARACTER])[0].removesuffix(
                        " (mlp)"
                    )
                )
            elif (
                "cinder glow (mlp)" in tags[tag_categories.CHARACTER]
                and "summer flare (mlp)" in tags[tag_categories.CHARACTER]
            ):
                output_directory = output_directory.joinpath(
                    "cinder glow, summer flare"
                )
            elif (
                "bon bon (mlp)" in tags[tag_categories.CHARACTER]
                and "sweetie drops (mlp)" in tags[tag_categories.CHARACTER]
            ):
                output_directory = output_directory.joinpath(
                    "bon bon, sweetie drops"
                )
            elif (
                "golden harvest (mlp)" in tags[tag_categories.CHARACTER]
                and "carrot top (mlp)" in tags[tag_categories.CHARACTER]
            ):
                output_directory = output_directory.joinpath(
                    "carrot top, golden harvest"
                )

        # rules for subfolders
        if tag_categories.SPECIES in tags and tag_categories.COPYRIGHT in tags:
            if "my little pony: pony life" in tags[tag_categories.COPYRIGHT]:
                output_directory = output_directory.joinpath("pony life")
            elif {"anthro", "human"} & tags[tag_categories.SPECIES]:
                output_directory = output_directory.joinpath("antro")

        # rules for /h/ folder
        if (
            tag_categories.RATING in tags
            and {"suggestive", "questionable", "explicit"} & tags["rating"]
        ):
            output_directory = output_directory.joinpath("h")
            if "suggestive" in tags[tag_categories.RATING]:
                output_directory = output_directory.joinpath("s")
            elif "questionable" in tags[tag_categories.RATING]:
                output_directory = output_directory.joinpath("q")
            elif "explicit" in tags[tag_categories.RATING]:
                output_directory = output_directory.joinpath("e")
        else:
            if (
                tag_categories.SPECIES in tags
                and tag_categories.COPYRIGHT in tags
                and "horse" in tags["species"]
                and "my little pony" not in tags["copyright"]
            ):
                output_directory = output_directory.joinpath("horse")
            elif "content" in tags and "vector" in tags["content"]:
                output_directory = output_directory.joinpath("vector")
            elif "content" in tags and "screencap" in tags["content"]:
                output_directory = output_directory.joinpath("screencap")
            elif (
                "content" in tags
                and {"simple background", "transparent background"}
                & tags["content"]
            ):
                output_directory = output_directory.joinpath("f")
            elif "content" in tags and "wallpaper" in tags["content"]:
                output_directory = output_directory.joinpath("wallpaper")
            elif "content" in tags and "photo" in tags["content"]:
                output_directory = output_directory.joinpath("photo")

        return output_directory


class DateBasedDirectory(FilesystemDirectoryManager):

    def choose_folder(self, tags: dict[str, set]) -> pathlib.Path:
        output_directory = pathlib.Path(config.initial_dir)

        current_date = datetime.datetime.now()

        return output_directory.joinpath(
            str(current_date.year),
            str(current_date.month),
            str(current_date.day),
        )


def find_folder(parsed_tags: dict[str, set]):
    dir_manager: FilesystemDirectoryManager | None = None

    if config.saving_path == config.PathSpecification.COLLECTION:
        dir_manager = TagBasedDirectory()
    elif config.saving_path == config.PathSpecification.DATE_DOWNLOADED:
        dir_manager = DateBasedDirectory()

    if dir_manager is None:
        raise ValueError(
            "unexpected value of config.saving_path: {}".format(
                config.saving_path
            )
        )

    return dir_manager.choose_folder(parsed_tags)
