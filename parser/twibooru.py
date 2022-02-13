import io
import os
import re

import requests

import config
import exceptions
import json
import logging
import pathlib
from . import Parser
import medialib_db

if config.do_transcode:
    import pyimglib.transcoding

FILENAME_PREFIX = 'tb'
ORIGIN = 'twibooru'

logger = logging.getLogger(__name__)


class TwibooruParser(Parser.Parser):
    def get_origin_name(self):
        return ORIGIN

    def get_filename_prefix(self):
        return 'tb'

    def getID(self) -> str:
        try:
            return str(self._parsed_data["id"])
        except KeyError as e:
            self._file_deleted_handing(FILENAME_PREFIX, self.input_id)
            raise e

    def getTagList(self) -> list:
        return self._parsed_data['tags'].split(', ')

    def parsehtml_get_image_route_name(self) -> str:
        return 'posts'

    def get_domain_name(self) -> str:
        return 'twibooru.org'

    def dataValidator(self, data):
        if 'image' not in data:
            raise KeyError("data has no \'image\'")
        if "original_format" not in data:
            raise KeyError("data has no original_format property")
        if 'representations' not in data:
            raise KeyError("data has no \'representations\'")
        if 'large' not in data['representations']:
            raise KeyError("not found large representation")

    def save_image(self, output_directory: str, data: dict, tags: dict = None) -> tuple[int, int, int, int]:
        if 'deletion_reason' in data and data['deletion_reason'] is not None:
            return self._file_deleted_handing(FILENAME_PREFIX, data['id'])
        if not os.path.isdir(output_directory):
            os.makedirs(output_directory)
        name = ''
        src_url = os.path.splitext(data['image'])[0] + '.' + data["original_format"]
        src_url = re.sub(r'\%', '', src_url)
        if 'file_name' in data and data['file_name'] is not None:
            name = "tb{} {}".format(
                data["id"],
                re.sub('[/\[\]:;|=*".?]', '', os.path.splitext(data["file_name"])[0])
            )
        else:
            name = str(data["id"])
        src_filename = os.path.join(output_directory, "{}.{}".format(name, data["original_format"]))

        metadata = {
            "title": data["file_name"],
            "origin": self.get_origin_name(),
            "id": data["id"]
        }

        print("filename", src_filename)
        print(src_url)

        result = None

        if config.do_transcode:
            args = (
                data["original_format"],
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
                except pyimglib.exceptions.NotIdentifiedFileFormat:
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

    def parseJSON(self, _type="images"):
        self.input_id = self.get_id_by_url(self._url)
        print("parseJSON", 'https://twibooru.org/' + self.input_id + '.json')
        request_data = None
        try:
            request_data = requests.get('https://twibooru.org/' + self.input_id + '.json')
        except Exception as e:
            print(e)
            return
        data = request_data.json()
        while "duplicate_of" in data:
            data = self.parseJSON(str(data["duplicate_of"]))
        if 'tags' not in data:
            data['tags'] = ""
        self._parsed_data = data
        return data


