import io
import json
import os
import pathlib
import re
import urllib.parse
import urllib.request
import logging

import exceptions
import medialib_db.srs_indexer

logger = logging.getLogger(__name__)

import requests

import config
from . import Parser


FILENAME_PREFIX = 'db'
ORIGIN = 'derpibooru'


class DerpibooruParser(Parser.Parser):

    def get_origin_name(self):
        return ORIGIN

    def getID(self) -> str:
        return str(self._parsed_data['image']["id"])

    def getTagList(self) -> list:
        return self._parsed_data['image']['tags']

    def parsehtml_get_image_route_name(self) -> str:
        return 'images'

    def get_domain_name(self) -> str:
        return DerpibooruParser.get_domain_name_s()

    @staticmethod
    def get_domain_name_s():
        return 'derpibooru.org'

    def get_filename_prefix(self):
        return FILENAME_PREFIX

    def parseJSON(self, url=None, type="images") -> dict:
        id = None
        if url is not None:
            id = url
        else:
            id = self.get_id_by_url(self._url)
        request_url = 'https://{}/api/v1/json/{}/{}'.format(self.get_domain_name_s(), type, urllib.parse.quote(id))
        print("parseJSON", request_url)
        try:
            request_data = requests.get(request_url)
        except Exception as e:
            print(e)
            return
        data = None
        if request_data.status_code == 404:
            raise IndexError("not founded \"{}\"".format(url))
        try:
            data = request_data.json()
        except json.JSONDecodeError as e:
            print("JSON decode error. HTTP status code:{} Raw data: {}".format(
                request_data.status_code, request_data.text))
            raise e
        while "duplicate_of" in data["image"] and data["image"]["duplicate_of"] is not None:
            data = self.parseJSON(str(data["image"]["duplicate_of"]))
        if 'tags' not in data['image']:
            data['image']['tags'] = []
        self._parsed_data = data
        return data

    def dataValidator(self, data):
        if 'image' not in data:
            raise KeyError("data has no \'image\'")
        data = data['image']
        if 'representations' not in data:
            raise KeyError("data has no \'representations\'")
        if 'full' not in data['representations']:
            raise KeyError("not found full representation")
        if type(data['representations']['full']) is not str:
            raise TypeError(
                "data['representations']['full'] is not str: "+data['representations']['full'].__class__.__name__
            )
        if type(os.path.splitext(data['representations']['full'])) is not tuple:
            raise TypeError(
                "os.path.splitext(data['representations']['full']) is not tuple: " + \
                os.path.splitext(data['representations']['full']).__class__.__name__
            )
        if type(os.path.splitext(data['representations']['full'])[0]) is not str:
            raise TypeError(
                "os.path.splitext(data['representations']['full'])[0] is not str: " + \
                os.path.splitext(data['representations']['full'])[0].__class__.__name__
            )
        if 'format' not in data:
            raise KeyError("data has no format property")
        if type(data["format"]) is not str:
            raise TypeError(
                "data[\"format\"] is not str: "+data["format"].__class__.__name__
            )
        if 'large' not in data['representations']:
            raise KeyError("not found large representation")

    def save_image(self, output_directory: str, data: dict, tags: dict = None) -> tuple[int, int, int, int]:
        if 'deletion_reason' in data['image'] and data['image']['deletion_reason'] is not None:
            return self._file_deleted_handing(FILENAME_PREFIX, data['image']['id'])
        if not os.path.isdir(output_directory):
            os.makedirs(output_directory)
        name = ''
        data = data['image']
        src_url = os.path.splitext(data['representations']['full'])[0] + '.' + data["format"].lower()
        if 'name' in data and data['name'] is not None:
            name = "{}{} {}".format(
                self.get_filename_prefix(),
                data["id"],
                re.sub('[/\[\]:;|=*".?]', '', os.path.splitext(data["name"])[0])
            )
        else:
            name = str(data["id"])
        src_filename = os.path.join(output_directory, "{}.{}".format(name, data["format"].lower()))

        metadata = {
            "title": data['name'],
            "origin": self.get_origin_name(),
            "id": data["id"]
        }

        print("filename", src_filename)
        print("image_url", src_url)

        result = None

        if config.do_transcode:
            args = (
                data['format'],
                data['representations']["large"],
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
                except exceptions.NotIdentifiedFileFormat:
                    result = self._file_deleted_handing(FILENAME_PREFIX, data['image']['id'])
        else:
            if self.enable_rewriting() or not os.path.isfile(src_filename):
                if not config.simulate:
                    self.download_file(src_filename, src_url)

        if config.use_medialib_db:
            self.medialib_db_register(data, src_filename, result, tags)

        if result is not None:
            return result[:4]
        else:
            return 0, 0, 0, 0
