import io
import json
import pathlib
import sys
from typing import Dict, Union, Set, Any

import config
import threading
import multiprocessing
import abc
import requests
import logging

import medialib_db

import mysql.connector

import re
from html.parser import HTMLParser

import os

if config.do_transcode:
    import pyimglib

logger = logging.getLogger(__name__)

ENABLE_REWRITING = False

TRANSCODE_FILES = {'png', 'jpg', 'jpeg', 'gif', 'webm', 'svg'}

downloader_thread = threading.Thread()
download_queue = []


if config.do_transcode:
    import pyimglib.transcoding
    from PIL.Image import DecompressionBombError


indexed_tags = set()

characters = set()

rating = set()

species = set()

content = set()


class Parser(abc.ABC):
    def __init__(self, url, parsed_data=None):
        self._url = url
        self._parsed_data = parsed_data

    def enable_rewriting(self):
        return ENABLE_REWRITING

    def _dump_parsed_data(self):
        if config.response_cache_dir is not None:
            config.response_cache_dir.mkdir(parents=True, exist_ok=True)
            f = config.response_cache_dir.joinpath(
                "{}{}.json".format(self.get_filename_prefix(), self.getID())
            ).open("w")
            json.dump(self._parsed_data, f)
            f.close()

    def _load_parsed_data(self):
        self.input_id = self.get_id_by_url(self._url)
        if config.response_cache_dir is not None:
            dump_file_path = config.response_cache_dir.joinpath(
                "{}{}.json".format(self.get_filename_prefix(), self.input_id)
            )
            if dump_file_path.exists():
                f = dump_file_path.open("r")
                self._parsed_data = json.load(f)
                f.close()
                print("LOADED FROM DUMP")
                return self._parsed_data
        return None

    @staticmethod
    def get_id_by_url(URL: str):
        return URL.split('?')[0].split('/')[-1]

    def append2queue(self, **kwargs):
        global downloader_thread
        global download_queue
        download_queue.append(kwargs)
        if not downloader_thread.is_alive():
            downloader_thread = threading.Thread(target=self.async_downloader)
            downloader_thread.start()

    def async_downloader(self):
        global download_queue
        while len(download_queue):
            print("Queue: lost {} images".format(len(download_queue)), file=sys.stderr)
            current_download = download_queue.pop()
            pipe=multiprocessing.Pipe()
            params = current_download
            params['pipe'] = pipe[1]
            process = multiprocessing.Process(target=self.save_image_old_interface, kwargs=params)
            process.start()
            import pyimglib.transcoding.statistics as stats
            stats.sumos, stats.sumsize, stats.avq, stats.items = pipe[0].recv()
            process.join()
            print("Queue: lost {} images".format(len(download_queue)), file=sys.stderr)

    @staticmethod
    def download_file(filename: str, src_url: str) -> None:
        request_data = requests.get(src_url)
        file = open(filename, 'wb')
        file.write(request_data.content)
        file.close()

    def in_memory_transcode(self, src_url, name, tags, output_directory, metadata):
        source = self.do_binary_request(src_url)
        transcoder = pyimglib.transcoding.get_memory_transcoder(
            source, output_directory, name, tags, metadata
        )
        return transcoder.transcode()

    @staticmethod
    def do_binary_request(url):
        request_data = requests.get(url)
        source = bytearray(request_data.content)
        return source

    @abc.abstractmethod
    def save_image(self, output_directory: str, data: dict, tags: dict = None):
        pass

    @abc.abstractmethod
    def parseJSON(self, _type="images"):
        pass

    def get_data(self):
        data = self._load_parsed_data()
        if data is None:
            data = self.parseJSON()
            if config.response_cache_dir is not None:
                self._dump_parsed_data()
        return data

    @abc.abstractmethod
    def parsehtml_get_image_route_name(self) -> str:
        pass

    @abc.abstractmethod
    def get_domain_name(self) -> str:
        pass

    @abc.abstractmethod
    def getTagList(self) -> list:
        pass

    @abc.abstractmethod
    def getID(self) -> str:
        pass

    @abc.abstractmethod
    def dataValidator(self, data):
        pass

    @abc.abstractmethod
    def get_filename_prefix(self):
        pass

    @abc.abstractmethod
    def get_origin_name(self):
        pass

    def parseHTML(self, image_id) -> dict:
        """
        Parse tags by HTML page.
        :param image_id:
        :return: {"tag name 1": "tag category 1", …}
        """
        global tags_parsed_data
        # derpibooru's API didn't provide method to get tag slug
        # image route also didn't contain that data
        tags_parsed_data = dict()
        request_url = 'https://{}/{}/{}'.format(
            self.get_domain_name(),
            self.parsehtml_get_image_route_name(),
            image_id
        )
        print("parseHTML", request_url, file=sys.stderr)
        try:
            request_data = requests.get(request_url)
        except Exception as e:
            print(e, file=sys.stderr)
            return
        raw_html = request_data.text

        class TagsParser(HTMLParser):
            def error(self, message):
                raise Exception(message)

            def handle_starttag(self, tag, attrs):
                if tag == 'span':
                    attributes = dict(attrs)
                    if "data-tag-name" in attributes.keys() and "data-tag-category" in attributes.keys():
                        tags_parsed_data[attributes["data-tag-name"]] = attributes["data-tag-category"]

        parser = TagsParser()
        parser.feed(raw_html)
        return tags_parsed_data

    def get_auto_copyright_tags(self):
        return {"my little pony"}

    def tagIndex(self) -> dict:
        global indexed_tags
        taglist = self.getTagList()
        tags_parsed_data = None

        def tag_register(tag_name, tag_category, tag_alias, connection):
            tag_id = medialib_db.tags_indexer.check_tag_exists(tag_name, tag_category, connection)
            if tag_id is None:
                tag_id = medialib_db.tags_indexer.insert_new_tag(
                    tag_name, tag_category, tag_alias, connection
                )
            else:
                tag_id = tag_id[0]
            return tag_id


        artist = set()
        originalCharacter = set()
        indexed_characters = set()
        indexed_rating = set()
        indexed_species = set()
        indexed_content = set()
        indexed_set = set()
        indexed_copyright = self.get_auto_copyright_tags()

        for tag in taglist:
            if "oc:" in tag:
                _oc = tag.split(':')[1]
                originalCharacter.add(_oc)
                if config.use_medialib_db:
                    connection = medialib_db.common.make_connection()

                    tag_register(
                        _oc, "original character", "original character:{}".format(_oc), connection
                    )

                    connection.close()
            elif "artist:" in tag:
                _artist = tag.split(':')[1]
                artist.add(_artist)
                if config.use_medialib_db:
                    connection = medialib_db.common.make_connection()

                    tag_register(
                        _artist, "artist", tag, connection
                    )

                    connection.close()
            elif '.' in tag or '-' in tag:
                continue
            elif config.use_medialib_db:
                connection = medialib_db.common.make_connection()
                result = medialib_db.tags_indexer.get_category_of_tag(tag, connection)
                if result is None:
                    if tags_parsed_data is None:
                        tags_parsed_data = self.parseHTML(self.getID())
                    INDEXED_TAG_CATEGORY = {
                        "character": indexed_characters,
                        "rating": indexed_rating,
                        "species": indexed_species
                    }
                    if tags_parsed_data[tag] in INDEXED_TAG_CATEGORY:
                        category_name = tags_parsed_data[tag]
                        INDEXED_TAG_CATEGORY[tags_parsed_data[tag]].add(tag)
                    elif "comic:" in tag or "art pack:" in tag or "fanfic:" in tag:
                        category_name = "set"
                        indexed_set.add(tag)
                    else:
                        category_name = "content"
                        indexed_content.add(tag)
                    medialib_db.tags_indexer.insert_new_tag(
                        tag, category_name, tag, connection
                    )
                else:
                    INDEXED_TAG_CATEGORY = {
                        "rating": indexed_rating,
                        "character": indexed_characters,
                        "species": indexed_species,
                        "set": indexed_set,
                        "copyright": indexed_copyright,
                        "content": indexed_content
                    }
                    if result[0] in INDEXED_TAG_CATEGORY:
                        INDEXED_TAG_CATEGORY[result[0]].add(tag)
                    else:
                        print(result)
                connection.close()
            else:
                if tag not in indexed_tags:
                    if tags_parsed_data is None:
                        tags_parsed_data = self.parseHTML(self.getID())
                    INDEXED_TAG_CATEGORY = {
                        "character": (characters, indexed_characters),
                        "rating": (rating, indexed_rating),
                        "species": (species, indexed_species)
                    }
                    if tags_parsed_data[tag] in INDEXED_TAG_CATEGORY:
                        INDEXED_TAG_CATEGORY[tags_parsed_data[tag]][0].add(tag)
                        INDEXED_TAG_CATEGORY[tags_parsed_data[tag]][1].add(tag)
                    else:
                        content.add(tag)
                        indexed_content.add(tag)
                    indexed_tags.add(tag)
                else:
                    INDEXED_TAG_CATEGORY = {
                        rating: indexed_rating,
                        characters: indexed_characters,
                        species: indexed_species,
                        content: indexed_content
                    }
                    for tag_category in INDEXED_TAG_CATEGORY:
                        if tag in tag_category:
                            INDEXED_TAG_CATEGORY[tag_category].add(tag)
        return {'artist': artist, 'original character': originalCharacter,
                'characters': indexed_characters, 'rating': indexed_rating,
                'species': indexed_species, 'content': indexed_content,
                'set': indexed_set, 'copyright': indexed_copyright}

    def _do_transcode(self, original_format, large_image, src_filename, output_directory, name, src_url, tags, metadata):
        if original_format in TRANSCODE_FILES:
            if self.enable_rewriting() or not os.path.isfile(src_filename) and \
                    not pyimglib.transcoding.check_exists(
                        src_filename,
                        output_directory,
                        name
                    ):
                try:
                    return self.in_memory_transcode(src_url, name, tags, output_directory, metadata)
                except DecompressionBombError:
                    src_url = \
                        'https:' + os.path.splitext(large_image)[0] + '.' + \
                        original_format
                    return self.in_memory_transcode(src_url, name, tags, output_directory,metadata)
            elif not pyimglib.transcoding.check_exists(src_filename, output_directory, name):
                transcoder = pyimglib.transcoding.get_file_transcoder(
                    src_filename, output_directory, name, tags, metadata
                )
                if transcoder is not None:
                    transcoder.transcode()
                else:
                    self.download_file(src_filename, src_url)
            elif config.enable_multiprocessing:
                return 0, 0, 0, 0, None
        else:
            if not os.path.isfile(src_filename):
                self.download_file(src_filename, src_url)
            return 0, 0, 0, 0, src_filename

    def _simulate_transcode(self, original_format, large_image, src_filename, output_directory, name, src_url, tags, metadata):
        if original_format in TRANSCODE_FILES:
            if self.enable_rewriting() or not os.path.isfile(src_filename) and \
                    not pyimglib.transcoding.check_exists(
                        src_filename,
                        output_directory,
                        name
                    ):
                return 0, 0, 0, 0, None
            elif not pyimglib.transcoding.check_exists(src_filename, output_directory, name):
                return 0, 0, 0, 0, None
            elif config.enable_multiprocessing:
                return 0, 0, 0, 0, None
            else:
                return 0, 0, 0, 0, None
        else:
            if not os.path.isfile(src_filename):
                pass
            return 0, 0, 0, 0, src_filename

    def save_image_old_interface(self, output_directory: str, data: dict, tags: dict = None, pipe=None) -> None:
        result = self.save_image(output_directory, data, tags)
        if pipe is not None:
            pipe.send(
                (
                    pyimglib.transcoding.statistics.sumos + result[0],
                    pyimglib.transcoding.statistics.sumsize + result[1],
                    pyimglib.transcoding.statistics.avq + result[2],
                    pyimglib.transcoding.statistics.items + result[3]
                )
            )
            pipe.close()

    def _file_deleted_handing(self, prefix, _id):
        logging.exception("deleted image {}".format(_id))
        if config.deleted_image_list_file_path is not None:
            deleted_list_f = pathlib.Path(config.deleted_image_list_file_path).open("a")
            parse_results = dict()
            try:
                parse_results = self.parseHTML(_id)
            except Exception as e:
                logger.exception("Some error was hapenned", e)
            deleted_list_f.write("{}{}: {}\n".format(
                prefix, _id, ", ".join([str(key) for key in parse_results.keys()])
            ))
            deleted_list_f.close()
        return 0, 0, 0, 0

    def medialib_db_register(self, data, src_filename, transcoding_result, tags):
        if config.simulate:
            return
        outname = src_filename
        if transcoding_result is not None:
            outname = transcoding_result[4]
            if type(outname) is io.TextIOWrapper:
                outname = outname.name
        elif not pathlib.Path(outname).exists():
            logger.error("NOT FOUNDED FILE")
            raise FileNotFoundError()

        _name = None
        media_type = None
        if 'name' in data:
            _name = data['name']
        if outname is not None:
            if ".srs" in outname:
                f = open(outname, "r")
                _data = json.load(f)
                f.close()
                media_type = medialib_db.srs_indexer.MEDIA_TYPE_CODES[_data['content']['media-type']]
            else:
                out_path = pathlib.Path(outname)
                if out_path.suffix.lower() in {".jpeg", ".jpg", ".png", ".webp", ".jxl", ".avif"}:
                    media_type = "image"
                elif out_path.suffix.lower() == ".gif":
                    media_type = "video-loop"
                elif out_path.suffix.lower() in {'.webm', ".mp4"}:
                    media_type = "video"
                else:
                    media_type = "image"
            _description = None
            if "description" in data and len(data['description']):
                _description = data['description']
            connection = medialib_db.common.make_connection()
            medialib_db.srs_indexer.register(
                pathlib.Path(outname),
                _name,
                media_type,
                _description,
                self.get_origin_name(),
                data["id"],
                tags,
                connection
            )
            connection.close()


def save_call(task: tuple[Parser, dict, dict, str]) -> tuple[int, int, int, int]:
    return task[0].save_image(*task[1:])
