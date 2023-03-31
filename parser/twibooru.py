import json
import logging
import os
import pathlib
import re
import time

import requests

from . import Parser
from .Parser import FileTypes

FILENAME_PREFIX = 'tb'
ORIGIN = 'twibooru'

logger = logging.getLogger(__name__)


class TwibooruParser(Parser.Parser):
    def identify_filetype(self) -> FileTypes:
        filetype = Parser.Parser.identify_by_mimetype(self.get_data()["post"]["mime_type"])
        if filetype == FileTypes.IMAGE and "animated" in self.get_data()["post"]['tags']:
            filetype = FileTypes.ANIMATION
    def get_origin_name(self):
        return ORIGIN

    def get_filename_prefix(self):
        return 'tb'

    def getID(self) -> str:
        try:
            return str(self._parsed_data["post"]["id"])
        except KeyError as e:
            self.file_deleted_handing(FILENAME_PREFIX, self.input_id)
            raise e

    def getTagList(self) -> list:
        return self.get_data()["post"]['tags']

    def parsehtml_get_image_route_name(self) -> str:
        return 'posts'

    def get_domain_name(self) -> str:
        return 'twibooru.org'

    def dataValidator(self, data):
        if 'view_url' not in data["post"]:
            raise KeyError("data has no \'image\'")
        if "format" not in data["post"]:
            raise KeyError("data has no original_format property")
        if 'representations' not in data["post"]:
            raise KeyError("data has no \'representations\'")
        if 'large' not in data["post"]['representations']:
            raise KeyError("not found large representation")

    def check_is_takedowned(self, data):
        return 'deletion_reason' in data["post"] and data["post"]['deletion_reason'] is not None

    def get_takedowned_content_info(self, data):
        return self.file_deleted_handing(FILENAME_PREFIX, data['post']['id'])

    def get_content_source_url(self, data):
        src_url = os.path.splitext(data["post"]["view_url"])[0] + '.' + data["post"]["format"]
        src_url = re.sub(r'\%', '', src_url)
        return src_url

    def get_output_filename(self, data, output_directory: pathlib.Path) -> tuple[str, pathlib.Path]:
        name = ''
        if 'name' in data["post"] and data["post"]['name'] is not None:
            name = "tb{} {}".format(
                data["post"]["id"],
                re.sub('[/\[\]:;|=*".?]', '', os.path.splitext(data["post"]["name"])[0])
            )
        else:
            name = str(data["id"])
        return name, output_directory.joinpath("{}.{}".format(name, data["post"]["format"]))

    def get_image_metadata(self, data):
        return {
            "title": data["post"]["name"],
            "origin": self.get_origin_name(),
            "id": data["post"]["id"]
        }

    def get_image_format(self, data):
        return data["post"]["format"]

    def get_big_thumbnail_url(self, data):
        return data["post"]['representations']["large"]

    def get_raw_content_data(self):
        return self.get_data()["post"]

    def parseJSON(self, _type="images", trial_count=2):
        self.input_id = self.get_id_by_url(self._url)
        request_url = 'https://twibooru.org/api/v3/posts/{}'.format(str(self.input_id))
        print("parseJSON", request_url)
        request_data = None
        try:
            request_data = requests.get(request_url)
        except Exception as e:
            print(e)
            return
        try:
            data = request_data.json()
        except json.JSONDecodeError as e:
            if trial_count > 0:
                logger.warning("JSON decode error. HTTP status code:{} Raw data: \n{}".format(
                    request_data.status_code, request_data.text))
                print("try again after 10 minutes")
                time.sleep(600)
                return self.parseJSON(type, trial_count-1)
            else:
                logger.error("JSON decode error. HTTP status code:{} Raw data: \n{}".format(
                    request_data.status_code, request_data.text))
                raise e
        while "duplicate_of" in data:
            data = self.parseJSON(str(data["post"]["duplicate_of"]))
        if 'tags' not in data["post"]:
            data["post"]['tags'] = ""
        self._parsed_data = data
        return data


