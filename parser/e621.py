import json
import logging
import os
import pathlib
import urllib
import urllib.parse

from . import exceptions

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
        request_url = 'https://{}/{}/{}.json'.format(self.get_domain_name_s(), _type, urllib.parse.quote(str(id)))
        if config.e621_login is not None and config.e621_API_KEY is not None:
            request_url += "?login={}&api_key={}".format(config.e621_login, config.e621_API_KEY)
        logger.info("parseJSON: {}".format(request_url))
        try:
            request_data = requests.get(request_url, headers=headers)
        except Exception as e:
            print(e)
            return
        data = None
        if request_data.status_code == 404:
            raise IndexError("not founded \"{}\"".format(url))
        logger.debug("STATUS CODE: {}".format(request_data.status_code))
        try:
            data = request_data.json()
        except json.JSONDecodeError as e:
            logger.error("JSON decode error. HTTP status code:{} Raw data: {}".format(
                request_data.status_code, request_data.text))
            raise e
        self._parsed_data = data
        return data

    def verify_not_takedowned(self, data):
        # TODO: find takedowned image
        return False

    def get_takedowned_content_info(self, data):
        # TODO: find takedowned image
        return None

    def get_content_source_url(self, data):
        return os.path.splitext(data['post']['file']['url'])[0] + '.' + data['post']['file']['ext'].lower()

    def get_output_filename(self, data, output_directory: pathlib.Path) -> tuple[str, pathlib.Path]:
        data = data['post']
        name = ''
        print(data["id"], data['file']['url'], data['file']['ext'])
        if data['file']['url'] is None or data['file']['ext'] is None:
            print(data)
        src_url = os.path.splitext(data['file']['url'])[0] + '.' + data['file']['ext'].lower()
        name = "{}{}".format(FILENAME_PREFIX, data["id"])
        return name, output_directory.joinpath("{}.{}".format(name, data['file']['ext'].lower()))

    def get_image_metadata(self, data):
        return {
            "title": None,
            "origin": self.get_origin_name(),
            "id": data['post']["id"]
        }

    def get_image_format(self, data):
        return data['post']['file']['ext']

    def get_big_thumbnail_url(self, data):
        return data['post']['sample']["url"]

    def get_raw_content_data(self):
        return self.get_data()["post"]


