from . import Parser
import config
import os
import re
import urllib.request
import urllib.error
import json
import requests

if config.enable_images_optimisations:
    from derpibooru_dl import imgOptimizer
    from PIL.Image import DecompressionBombError

characters = {'applejack', 'fluttershy', 'twilight sparkle', 'rainbow dash', 'pinkie pie', 'rarity', 'derpy hooves',
              'lyra heartstrings', 'zecora', 'apple bloom', 'sweetie belle', 'scootaloo', 'princess cadance',
              'princess celestia', 'princess luna', 'maud pie', 'octavia', 'gilda', 'gabby', 'princess flurry heart',
              'sunset shimmer', 'starlight glimmer', 'trixie', 'coco pomel', 'spitfire', 'princess ember', 'fleetfoot',
              'cutie mark crusaders', 'spike', 'moondancer', 'dj pon3', 'tempest shadow', 'silverstream', 'yona',
              'smolder', 'gallus', 'ocellus', 'sandbar', 'princess skystar', 'limestone pie', 'autumn blaze',
              'cozy glow', 'arizona cow'}

rating = {'safe', 'suggestive', 'questionable', 'explicit', 'semi-grimdark', 'grimdark', 'guro', 'shipping',
                'portrait'}

art_type = {'traditional art', 'digital art', 'sketch', 'vector', 'simple background', 'animated', 'wallpaper',
            'screencap', 'photo', '3d', 'transparent background', 'equestria girls'}

species = {'pony', 'anthro', 'humanisation', 'horse', 'hoers', 'pegasus', 'mare', 'unicorn', 'bipedal', 'earth pony',
             'semi-anthro', 'g1', 'g2', 'g3', 'realistic anatomy'}

content = {'plot', 'lided paper', 'pencil drawing', 'solo', 'flying', 'younger', 'source filmmaker', 'snow', 'cuddling',
           'duo', 'text', 'wings', 'magic', 'prone', 'looking at you', 'socks', 'bust', 'lesbian', 'bed', 'selfie',
           'window', 'sitting', 'nudity', 'looking at each other', 'pillow', 'fat', 'blood', 'diaper'}


class TwibooruParser(Parser.Parser):
    def save_image(self, output_directory: str, data: dict, tags: dict = None, pipe=None):
        if 'deletion_reason' in data:
            if config.enable_images_optimisations and config.enable_multiprocessing:
                imgOptimizer.pipe_send(pipe)
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
                if not os.path.isfile(src_filename) and not imgOptimizer.check_exists(src_filename, output_directory,
                                                                                      name):
                    try:
                        self.in_memory_transcode(src_url, name, tags, output_directory, pipe)
                    except DecompressionBombError:
                        src_url = \
                            'https:' + os.path.splitext(data['representations']["large"])[0] + '.' + \
                            data["original_format"]
                        self.in_memory_transcode(src_url, name, tags, output_directory, pipe)
                elif not imgOptimizer.check_exists(src_filename, output_directory, name):
                    transcoder = imgOptimizer.get_file_transcoder(
                        src_filename, output_directory, name, tags, pipe
                    )
                    transcoder.transcode()
                elif config.enable_multiprocessing:
                    imgOptimizer.pipe_send(pipe)
            else:
                if not os.path.isfile(src_filename):
                    self.download_file(src_filename, src_url)
                if config.enable_multiprocessing:
                    imgOptimizer.pipe_send(pipe)
        else:
            if not os.path.isfile(src_filename):
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

    def tagIndex(self):
        rawtags = self._parsed_data['tags']
        taglist = rawtags.split(', ')
        artist = ''
        originalCharacter = []
        tagset = set()
        for tag in taglist:
            if ':' in set(tag):
                parsebuf = tag.split(':')
                if parsebuf[0] == 'artist':
                    artist = parsebuf[1]
                elif parsebuf[0] == 'oc':
                    originalCharacter.append(parsebuf[1])
            else:
                tagset.add(tag)
        indexed_characters = characters & tagset
        indexed_rating = rating & tagset
        indexed_art_types = art_type & tagset
        indexed_species = species & tagset
        indexed_content = content & tagset
        return {'artist': artist, 'original character': originalCharacter,
                'characters': indexed_characters, 'rating': indexed_rating,
                'art_type': indexed_art_types, 'species': indexed_species,
                'content': indexed_content}


    @staticmethod
    def do_binary_request(url):
        request_data = requests.get(url)
        source = bytearray(request_data.content)
        return source

