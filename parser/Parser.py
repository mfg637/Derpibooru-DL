import sys

import config
import threading
import multiprocessing
import abc
import requests

import mysql.connector

import re
from html.parser import HTMLParser

if config.enable_images_optimisations:
    import pyimglib_transcoding

ENABLE_REWRITING = False


downloader_thread = threading.Thread()
download_queue = []


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

indexed_tags = set()

characters = set()

rating = set()

species = set()

content = set()


class Parser(abc.ABC):
    def __init__(self, url, parsed_data=None):
        self._url = url
        self._parsed_data = parsed_data

    def enable_rewriting(self):
        return ENABLE_REWRITING

    @staticmethod
    def get_id_by_url(URL: str):
        return URL.split('?')[0].split('/')[-1]

    def append2queue(self, **kwargs):
        global downloader_thread
        global download_queue
        download_queue.append(kwargs)
        if not downloader_thread.is_alive():
            downloader_thread = threading.Thread(target=self.async_downloader)
            downloader_thread.start()

    def async_downloader(self):
        global download_queue
        while len(download_queue):
            print("Queue: lost {} images".format(len(download_queue)), file=sys.stderr)
            current_download = download_queue.pop()
            pipe=multiprocessing.Pipe()
            params = current_download
            params['pipe'] = pipe[1]
            process = multiprocessing.Process(target=self.save_image, kwargs=params)
            process.start()
            import pyimglib_transcoding.statistics as stats
            stats.sumos, stats.sumsize, stats.avq, stats.items = pipe[0].recv()
            process.join()
            print("Queue: lost {} images".format(len(download_queue)), file=sys.stderr)

    @staticmethod
    def download_file(filename: str, src_url: str) -> None:
        request_data = requests.get(src_url)
        file = open(filename, 'wb')
        file.write(request_data.content)
        file.close()

    def in_memory_transcode(self, src_url, name, tags, output_directory, pipe):
        source = self.do_binary_request(src_url)
        transcoder = pyimglib_transcoding.get_memory_transcoder(
            source, output_directory, name, tags, pipe
        )
        transcoder.transcode()

    @staticmethod
    def do_binary_request(url):
        request_data = requests.get(url)
        source = bytearray(request_data.content)
        return source

    @abc.abstractmethod
    def save_image(self, output_directory: str, data: dict, tags: dict = None, pipe = None):
        pass

    @abc.abstractmethod
    def parseJSON(self, _type="images"):
        pass

    @abc.abstractmethod
    def parsehtml_get_image_route_name(self) -> str:
        pass

    @abc.abstractmethod
    def get_domain_name(self) -> str:
        pass

    @abc.abstractmethod
    def getTagList(self) -> list:
        pass

    @abc.abstractmethod
    def getID(self) -> str:
        pass

    @abc.abstractmethod
    def dataValidator(self, data):
        pass

    @abc.abstractmethod
    def get_filename_prefix(self):
        pass

    def tagIndex(self):
        global indexed_tags
        taglist = self.getTagList()
        tags_parsed_data = None

        def mysql_escafe_quotes(_string):
            return re.sub("\"", "\\\"", _string)

        def parseHTML(image_id):
            global tags_parsed_data
            # derpibooru's API didn't provide method to get tag slug
            # image route also didn't contain that data
            tags_parsed_data = dict()
            request_url = 'https://{}/{}/{}'.format(
                self.get_domain_name(),
                self.parsehtml_get_image_route_name(),
                image_id
            )
            print("parseHTML", request_url, file=sys.stderr)
            try:
                request_data = requests.get(request_url)
            except Exception as e:
                print(e, file=sys.stderr)
                return
            raw_html = request_data.text

            class TagsParser(HTMLParser):
                def error(self, message):
                    raise Exception(message)

                def handle_starttag(self, tag, attrs):
                    if tag == 'span':
                        attributes = dict(attrs)
                        if "data-tag-name" in attributes.keys() and "data-tag-category" in attributes.keys():
                            tags_parsed_data[attributes["data-tag-name"]] = attributes["data-tag-category"]
            parser = TagsParser()
            parser.feed(raw_html)
            return tags_parsed_data


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
                    if tags_parsed_data is None:
                        tags_parsed_data = parseHTML(self.getID())
                    if tags_parsed_data[tag] == "character":
                        category_name = "character"
                        indexed_characters.add(tag)
                    elif tags_parsed_data[tag] == "rating":
                        category_name = "rating"
                        indexed_rating.add(tag)
                    elif tags_parsed_data[tag] == "species":
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
                    if tags_parsed_data is None:
                        tags_parsed_data = parseHTML(self.getID())
                    if tags_parsed_data[tag] == "character":
                        characters.add(tag)
                        indexed_characters.add(tag)
                    elif tags_parsed_data[tag] == "rating":
                        rating.add(tag)
                        indexed_rating.add(tag)
                    elif tags_parsed_data[tag] == "species":
                        species.add(tag)
                        indexed_species.add(tag)
                    else:
                        content.add(tag)
                        indexed_content.add(tag)
                    indexed_tags.add(tag)
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

