import io
import logging
import os
import pathlib
import json
import urllib

import derpibooru_dl.tagResponse
import pyimglib

import exceptions
import medialib_db

logger = logging.getLogger(__name__)

import requests

import config
from . import Parser


FILENAME_PREFIX = 'ef'
ORIGIN = 'e621'


class E621Parser(Parser.Parser):

    def parsehtml_get_image_route_name(self) -> str:
        pass

    def get_domain_name(self) -> str:
        return E621Parser.get_domain_name_s()

    @staticmethod
    def get_domain_name_s():
        return 'e621.net'

    def getTagList(self) -> list:
        pass

    def getID(self) -> str:
        return str(self._parsed_data['post']["id"])

    def dataValidator(self, data):
        pass

    def get_filename_prefix(self):
        return FILENAME_PREFIX

    def get_origin_name(self):
        return ORIGIN

    def parseJSON(self, url=None, _type="posts"):
        headers = {
            'User-Agent': 'Derpibooru-DL (by mfg637) (https://github.com/mfg637/Derpibooru-DL)'
        }

        id = None
        if url is not None:
            id = url
        else:
            id = self.get_id_by_url(self._url)
        request_url = 'https://{}/{}/{}.json'.format(self.get_domain_name_s(), _type, urllib.parse.quote(id))
        if config.e621_login is not None and config.e621_API_KEY is not None:
            request_url += "?login={}&api_key={}".format(config.e621_login, config.e621_API_KEY)
        print("parseJSON", request_url)
        try:
            request_data = requests.get(request_url, headers=headers)
        except Exception as e:
            print(e)
            return
        data = None
        if request_data.status_code == 404:
            raise IndexError("not founded \"{}\"".format(url))
        print("STATUS CODE", request_data.status_code)
        try:
            data = request_data.json()
        except json.JSONDecodeError as e:
            print("JSON decode error. HTTP status code:{} Raw data: {}".format(
                request_data.status_code, request_data.text))
            raise e
        self._parsed_data = data
        return data

        # test stub
        f = open("./e621_sample_post_3109846.json", "r")
        self._parsed_data = json.load(f)
        f.close()

    def tagIndex(self) -> dict:

        def tag_register(tag_name, tag_category, tag_alias):
            tag_id = medialib_db.tags_indexer.check_tag_exists(tag_name, tag_category, auto_open_connection=False)
            if tag_id is None:
                tag_id = medialib_db.tags_indexer.insert_new_tag(
                    tag_name, tag_category, tag_alias, auto_open_connection=False
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
        indexed_copyright = set()

        medialib_db.common.open_connection_if_not_opened()

        for tag in self._parsed_data['post']['tags']['copyright']:
            _tag = tag.replace("_", " ")
            indexed_copyright.add(_tag)

        for tag in self._parsed_data['post']['tags']['character']:
            _tag = tag
            if "_(mlp)" in tag:
                indexed_copyright.add("my little pony")
                _tag = tag.replace("_(mlp)", "")
            _tag = _tag.replace("_", " ")
            indexed_characters.add(_tag)
            tag_register(
                _tag, 'character', _tag
            )

        for tag in indexed_copyright:
            tag_register(
                tag, 'copyright', tag
            )

        for tag in self._parsed_data['post']['tags']['species']:
            indexed_species.add(tag.replace("_", " "))

        for tag in self._parsed_data['post']['tags']['artist']:
            _tag = tag.replace("_", " ")
            artist.add(_tag)
            tag_alias = "{}:{}".format("artist", _tag)
            tag_register(
                _tag, 'artist', tag_alias
            )

        rating_table = {
            "s": "safe",
            "q": "questionable",
            "e": "explicit"
        }
        indexed_rating.add(rating_table[self._parsed_data['post']['rating']])
        tag_register(
            rating_table[self._parsed_data['post']['rating']],
            'rating',
            rating_table[self._parsed_data['post']['rating']]
        )

        for tag in self._parsed_data['post']['tags']['general']:
            if tag == "anthro":
                indexed_species.add("anthro")
            else:
                _tag = tag.replace("_", " ")
                indexed_content.add(_tag)
                tag_register(
                    _tag, 'content', _tag
                )

        for tag in indexed_species:
            tag_register(
                tag, 'species', tag
            )

        medialib_db.common.close_connection_if_not_closed()

        return {'artist': artist, 'original character': originalCharacter,
                'characters': indexed_characters, 'rating': indexed_rating,
                'species': indexed_species, 'content': indexed_content,
                'set': indexed_set, 'copyright': indexed_copyright}

    # def test(self):
    #     self.parseJSON()
    #     tags = self.tagIndex()
    #     print(tags)
    #     outdir = derpibooru_dl.tagResponse.find_folder(tags)
    #     print(outdir)
    #     self.save_image(outdir, self._parsed_data, tags)

    def save_image(self, output_directory: str, data: dict, tags: dict = None):
        #if 'deletion_reason' in data['image'] and data['image']['deletion_reason'] is not None:
        #    return self._file_deleted_handing(FILENAME_PREFIX, data['image']['id'])
        if not os.path.isdir(output_directory):
            os.makedirs(output_directory)
        name = ''
        data = data['post']
        print(data["id"], data['file']['url'], data['file']['ext'])
        if data['file']['url'] is None or data['file']['ext'] is None:
            print(data)
        src_url = os.path.splitext(data['file']['url'])[0] + '.' + data['file']['ext'].lower()
        name = "{}{}".format(FILENAME_PREFIX, data["id"])
        src_filename = os.path.join(output_directory, "{}.{}".format(name, data['file']['ext'].lower()))

        metadata = {
            "title": None,
            "origin": self.get_origin_name(),
            "id": data["id"]
        }

        print("filename", src_filename)
        print("image_url", src_url)

        result = None

        if config.do_transcode:
            args = (
                data['file']['ext'],
                data['sample']["url"],
                src_filename,
                output_directory,
                name,
                src_url,
                tags,
                metadata
            )
            if config.simulate:
                self._simulate_transcode(*args)
            else:
                try:
                    result = self._do_transcode(*args)
                except pyimglib.exceptions.NotIdentifiedFileFormat:
                    result = self._file_deleted_handing(FILENAME_PREFIX, data['image']['id'])
        else:
            if self.enable_rewriting() or not os.path.isfile(src_filename):
                if not config.simulate:
                    self.download_file(src_filename, src_url)
        outname = src_filename

        if config.use_medialib_db:
            self.medialib_db_register(data, src_filename, result, tags)

        if result is not None:
            return result[:4]
        else:
            return 0, 0, 0, 0

