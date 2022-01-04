import pathlib
import sys

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

    def tagIndex(self) -> dict:
        global indexed_tags
        taglist = self.getTagList()
        tags_parsed_data = None

        def mysql_escafe_quotes(_string):
            return re.sub("\"", "\\\"", _string)


        artist = set()
        originalCharacter = set()
        indexed_characters = set()
        indexed_rating = set()
        indexed_species = set()
        indexed_content = set()
        indexed_set = set()
        for tag in taglist:
            if "oc:" in tag:
                _oc = tag.split(':')[1]
                originalCharacter.add(_oc)
                if config.use_medialib_db:
                    medialib_db.common.open_connection_if_not_opened()

                    medialib_db.tags_indexer.tag_register(
                        _oc, "original character", "original character:{}".format(_oc)
                    )

                    medialib_db.common.close_connection_if_not_closed()
            elif "artist:" in tag:
                _artist = tag.split(':')[1]
                artist.add(_artist)
                if config.use_medialib_db:
                    medialib_db.common.open_connection_if_not_opened()

                    medialib_db.tags_indexer.tag_register(
                        _artist, "artist", tag
                    )

                    medialib_db.common.close_connection_if_not_closed()
            elif '.' in tag or '-' in tag:
                continue
            elif config.use_medialib_db:
                medialib_db.common.open_connection_if_not_opened()
                result = medialib_db.tags_indexer.get_category_of_tag(tag, auto_open_connection=False)
                if result is None:
                    if tags_parsed_data is None:
                        tags_parsed_data = self.parseHTML(self.getID())
                    if tags_parsed_data[tag] == "character":
                        category_name = "character"
                        indexed_characters.add(tag)
                    elif tags_parsed_data[tag] == "rating":
                        category_name = "rating"
                        indexed_rating.add(tag)
                    elif tags_parsed_data[tag] == "species":
                        category_name = "species"
                        indexed_species.add(tag)
                    elif "comic:" in tag:
                        category_name = "set"
                        indexed_set.add(tag)
                    else:
                        category_name = "content"
                        indexed_content.add(tag)
                    q_tag = mysql_escafe_quotes(tag)
                    medialib_db.tags_indexer.insert_new_tag(
                        q_tag, category_name, q_tag, auto_open_connection=False
                    )
                else:
                    if result[0] == "rating":
                        indexed_rating.add(tag)
                    elif result[0] == "characters":
                        indexed_characters.add(tag)
                    elif result[0] == "species":
                        indexed_species.add(tag)
                    elif result[0] == "set":
                        indexed_set.add(tag)
                    elif result[0] == "content":
                        indexed_content.add(tag)
                    else:
                        print(result)
                medialib_db.common.close_connection_if_not_closed()
            else:
                if tag not in indexed_tags:
                    if tags_parsed_data is None:
                        tags_parsed_data = self.parseHTML(self.getID())
                    if tags_parsed_data[tag] == "character":
                        characters.add(tag)
                        indexed_characters.add(tag)
                    elif tags_parsed_data[tag] == "rating":
                        rating.add(tag)
                        indexed_rating.add(tag)
                    elif tags_parsed_data[tag] == "species":
                        species.add(tag)
                        indexed_species.add(tag)
                    else:
                        content.add(tag)
                        indexed_content.add(tag)
                    indexed_tags.add(tag)
                else:
                    if tag in rating:
                        indexed_rating.add(tag)
                    elif tag in characters:
                        indexed_characters.add(tag)
                    elif tag in species:
                        indexed_species.add(tag)
                    elif tag in content:
                        indexed_content.add(tag)
        return {'artist': artist, 'original character': originalCharacter,
                'characters': indexed_characters, 'rating': indexed_rating,
                'species': indexed_species, 'content': indexed_content,
                'set': indexed_set}

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
                transcoder.transcode()
            elif config.enable_multiprocessing:
                return 0, 0, 0, 0, src_filename
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
                return 0, 0, 0, 0, src_filename
            elif not pyimglib.transcoding.check_exists(src_filename, output_directory, name):
                return 0, 0, 0, 0, src_filename
            elif config.enable_multiprocessing:
                return 0, 0, 0, 0, src_filename
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


def save_call(task: tuple[Parser, dict, dict, str]) -> tuple[int, int, int, int]:
    return task[0].save_image(*task[1:])
