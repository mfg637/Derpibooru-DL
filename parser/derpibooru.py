import json
import urllib.parse
import urllib.request
import config
import os
import re
import mysql.connector
import requests

from . import Parser

if config.enable_images_optimisations:
    from derpibooru_dl import imgOptimizer
    from PIL.Image import DecompressionBombError


mysql_connection = None
mysql_cursor = None
if config.use_mysql:
    mysql_connection = mysql.connector.connect(
        host=config.mysql_host,
        user=config.mysql_user,
        passwd=config.mysql_password,
        database=config.mysql_database
    )
mysql_cursor = mysql_connection.cursor()

indexed_tags = dict()

characters = set()

rating = set()

species = set()

content = set()


class DerpibooruParser(Parser.Parser):
    @staticmethod
    def get_domain_name():
        return 'derpibooru.org'

    @staticmethod
    def get_filename_prefix():
        return 'db'

    def parseJSON(self, url=None, type="images"):
        id = None
        if url is not None:
            id = url
        else:
            id = self.get_id_by_url(self._url)
        request_url = 'https://{}/api/v1/json/{}/{}'.format(self.get_domain_name(), type, urllib.parse.quote(id))
        print("parseJSON", request_url)
        try:
            request_data = requests.get(request_url)
        except Exception as e:
            print(e)
            return
        data = request_data.json()
        while "duplicate_of" in data:
            data = self.parseJSON(str(data["duplicate_of"]))
        self._parsed_data = data
        return data

    def save_image(self, output_directory: str, data: dict, tags: dict = None, pipe=None) -> None:
        if 'deletion_reason' in data and data['deletion_reason'] is not None:
            print('DELETED')
            if config.enable_images_optimisations and config.enable_multiprocessing:
                imgOptimizer.pipe_send(pipe)
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

        print("filename", src_filename)
        print("image_url", src_url)

        if config.enable_images_optimisations:
            if data["format"] in {'png', 'jpg', 'jpeg', 'gif'}:
                if not os.path.isfile(src_filename) and \
                        not imgOptimizer.check_exists(
                            src_filename,
                            output_directory,
                            name
                        ):
                    try:
                        self.in_memory_transcode(src_url, name, tags, output_directory, pipe)
                    except DecompressionBombError:
                        src_url = \
                            'https:' + os.path.splitext(data['representations']["large"])[0] + '.' + \
                            data["format"]
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

    def tagIndex(self):
        taglist = self._parsed_data['image']['tags']

        def mysql_escafe_quotes(_string):
            return re.sub("\"", "\\\"", _string)

        def get_JSON_Data(tag):
            tag = re.sub("/", "-fwslash-", tag)
            tag = re.sub(":", "-colon-", tag)
            tag = urllib.parse.quote(tag)
            tag = re.sub("%20", "+", tag)
            tag = re.sub("%27", '\'', tag)
            return self.parseJSON(tag, 'tags')['tag']

        artist = set()
        originalCharacter = set()
        indexed_characters = set()
        indexed_rating = set()
        indexed_species = set()
        indexed_content = set()
        for tag in taglist:
            if "oc:" in tag:
                originalCharacter.add(tag.split(':')[1])
            elif "artist:" in tag:
                artist.add(tag.split(':')[1])
            elif '.' in tag or '-' in tag:
                continue
            elif config.use_mysql:
                query = "SELECT category FROM tag_categories WHERE tag=\"{}\";".format(
                    mysql_escafe_quotes(tag)
                )
                mysql_cursor.execute(query)
                result = mysql_cursor.fetchone()
                if result is None:
                    category_name = ""
                    indexed_tag = get_JSON_Data(tag)
                    if indexed_tag['category'] == "character":
                        category_name = "character"
                        indexed_characters.add(tag)
                    elif indexed_tag['category'] == "rating":
                        category_name = "rating"
                        indexed_rating.add(tag)
                    elif indexed_tag['category'] == "species":
                        category_name = "species"
                        indexed_species.add(tag)
                    else:
                        category_name = "content"
                        indexed_content.add(tag)
                    insert_query = "INSERT INTO tag_categories VALUES (\"{}\", \"{}\");".format(
                        mysql_escafe_quotes(tag), category_name
                    )
                    mysql_cursor.execute(insert_query)
                    mysql_connection.commit()
                else:
                    if result[0] == "rating":
                        indexed_rating.add(tag)
                    elif result[0] == "character":
                        indexed_characters.add(tag)
                    elif result[0] == "species":
                        indexed_species.add(tag)
                    elif result[0] == "content":
                        indexed_content.add(tag)
                    else:
                        print(result)
            else:
                if tag not in indexed_tags:
                    indexed_tags[tag] = get_JSON_Data(tag)
                    if indexed_tags[tag]['category'] == "character":
                        characters.add(tag)
                        indexed_characters.add(tag)
                    elif indexed_tags[tag]['category'] == "rating":
                        rating.add(tag)
                        indexed_rating.add(tag)
                    elif indexed_tags[tag]['category'] == "species":
                        species.add(tag)
                        indexed_species.add(tag)
                    else:
                        content.add(tag)
                        indexed_content.add(tag)
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
                'species': indexed_species, 'content': indexed_content}
