import json
import logging
import os
import pathlib
import re
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

import requests

from . import Parser


FILENAME_PREFIX = 'db'
ORIGIN = 'derpibooru'


class DerpibooruParser(Parser.Parser):

    def get_origin_name(self):
        return ORIGIN

    def getID(self) -> str:
        return str(self.get_data()['image']["id"])

    def getTagList(self) -> list:
        return self.get_data()['image']['tags']

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
        request_url = 'https://{}/api/v1/json/{}/{}'.format(self.get_domain_name_s(), type, urllib.parse.quote(str(id)))
        logger.debug("url: {}".format(url))
        logger.info("parseJSON: {}".format(request_url))
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

    def verify_not_takedowned(self, data):
        return 'deletion_reason' in data['image'] and data['image']['deletion_reason'] is not None

    def get_takedowned_content_info(self, data):
        return self.file_deleted_handing(FILENAME_PREFIX, data['image']['id'])

    def get_content_source_url(self, data):
        return os.path.splitext(data['image']['representations']['full'])[0] + '.' + data['image']["format"].lower()

    def get_output_filename(self, data, output_directory: pathlib.Path) -> tuple[str, pathlib.Path]:
        data = data['image']
        name = ''
        if 'name' in data and data['name'] is not None:
            name = "{}{} {}".format(
                self.get_filename_prefix(),
                data["id"],
                re.sub('[/\[\]:;|=*".?]', '', os.path.splitext(data["name"])[0])
            )
        else:
            name = "{}{}".format(self.get_filename_prefix(), data["id"])
        return name, output_directory.joinpath("{}.{}".format(name, data["format"].lower()))

    def get_image_metadata(self, data):
        return {
            "title": data['image']['name'],
            "origin": self.get_origin_name(),
            "id": data['image']["id"]
        }

    def get_image_format(self, data):
        return data['image']['format']

    def get_big_thumbnail_url(self, data):
        return data['image']['representations']["large"]

    def get_raw_content_data(self):
        return self.get_data()['image']
