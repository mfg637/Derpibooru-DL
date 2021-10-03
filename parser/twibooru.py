from . import Parser
import config
import os
import re
import requests

if config.enable_images_optimisations:
    import pyimglib.transcoding
    from PIL.Image import DecompressionBombError


FILENAME_PREFIX = 'tb'


class TwibooruParser(Parser.Parser):
    def get_filename_prefix(self):
        return 'tb'

    def getID(self) -> str:
        return str(self._parsed_data["id"])

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

    def save_image(self, output_directory: str, data: dict, tags: dict = None, pipe=None):
        if 'deletion_reason' in data:
            if config.enable_images_optimisations and config.enable_multiprocessing:
                pyimglib_transcoding.statistics.pipe_send(pipe)
            return
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

        print("filename", src_filename)
        print(src_url)

        if config.enable_images_optimisations:
            if data["original_format"] in {'png', 'jpg', 'jpeg', 'gif'}:
                if self.enable_rewriting() or not os.path.isfile(src_filename) and not pyimglib_transcoding.check_exists(
                        src_filename,
                        output_directory,
                        name
                ):
                    try:
                        self.in_memory_transcode(src_url, name, tags, output_directory, pipe)
                    except DecompressionBombError:
                        src_url = \
                            'https:' + os.path.splitext(data['representations']["large"])[0] + '.' + \
                            data["original_format"]
                        self.in_memory_transcode(src_url, name, tags, output_directory, pipe)
                elif not pyimglib_transcoding.check_exists(src_filename, output_directory, name):
                    transcoder = pyimglib_transcoding.get_file_transcoder(
                        src_filename, output_directory, name, tags, pipe
                    )
                    transcoder.transcode()
                elif config.enable_multiprocessing:
                    pyimglib_transcoding.statistics.pipe_send(pipe)
            else:
                if not os.path.isfile(src_filename):
                    self.download_file(src_filename, src_url)
                if config.enable_multiprocessing:
                    pyimglib_transcoding.statistics.pipe_send(pipe)
        else:
            if self.enable_rewriting() or not os.path.isfile(src_filename):
                self.download_file(src_filename, src_url)

    def parseJSON(self, _type="images"):
        id = self.get_id_by_url(self._url)
        print("parseJSON", 'https://twibooru.org/' + id + '.json')
        request_data = None
        try:
            request_data = requests.get('https://twibooru.org/' + id + '.json')
        except Exception as e:
            print(e)
            return
        data = request_data.json()
        while "duplicate_of" in data:
            data = self.parseJSON(str(data["duplicate_of"]))
        self._parsed_data = data
        return data

