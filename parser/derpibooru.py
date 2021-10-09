import json
import urllib.parse
import urllib.request
import config
import os
import re
import requests

import parser.Parser
from . import Parser

if config.enable_images_optimisations:
    import pyimglib.transcoding
    from PIL.Image import DecompressionBombError

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

    def parseJSON(self, url=None, type="images"):
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
        try:
            data = request_data.json()
        except json.JSONDecodeError as e:
            print("JSON decode error. HTTP status code:{} Raw data: {}".format(
                request_data.status_code, request_data.text))
            raise e
        while "duplicate_of" in data:
            data = self.parseJSON(str(data["duplicate_of"]))
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

    def save_image(self, output_directory: str, data: dict, tags: dict = None, pipe=None) -> None:
        if 'deletion_reason' in data and data['deletion_reason'] is not None:
            print('DELETED')
            if config.enable_images_optimisations and config.enable_multiprocessing:
                pyimglib.transcoding.statistics.pipe_send(pipe)
            return
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

        if config.enable_images_optimisations:
            if data["format"] in Parser.TRANSCODE_FILES:
                if self.enable_rewriting() or not os.path.isfile(src_filename) and \
                        not pyimglib.transcoding.check_exists(
                            src_filename,
                            output_directory,
                            name
                        ):
                    try:
                        self.in_memory_transcode(src_url, name, tags, output_directory, pipe, metadata)
                    except DecompressionBombError:
                        src_url = \
                            'https:' + os.path.splitext(data['representations']["large"])[0] + '.' + \
                            data["format"]
                        self.in_memory_transcode(src_url, name, tags, output_directory, pipe, metadata)
                elif not pyimglib.transcoding.check_exists(src_filename, output_directory, name):
                    transcoder = pyimglib.transcoding.get_file_transcoder(
                        src_filename, output_directory, name, tags, pipe, metadata
                    )
                    transcoder.transcode()
                elif config.enable_multiprocessing:
                    pyimglib.transcoding.statistics.pipe_send(pipe)
            else:
                if not os.path.isfile(src_filename):
                    self.download_file(src_filename, src_url)
                if config.enable_multiprocessing:
                    pyimglib.transcoding.statistics.pipe_send(pipe)
        else:
            if self.enable_rewriting() or not os.path.isfile(src_filename):
                self.download_file(src_filename, src_url)
