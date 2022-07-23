import abc
import json
import logging
import pathlib
import sys
from html.parser import HTMLParser

import requests

import config
import medialib_db

logger = logging.getLogger(__name__)



indexed_tags = set()

characters = set()

rating = set()

species = set()

content = set()


class Parser(abc.ABC):
    def __init__(self, url, parsed_data=None):
        self._url = url
        self._parsed_data = parsed_data

    def _dump_parsed_data(self):
        if config.response_cache_dir is not None:
            config.response_cache_dir.mkdir(parents=True, exist_ok=True)
            f = config.response_cache_dir.joinpath(
                "{}{}.json".format(self.get_filename_prefix(), self.getID())
            ).open("w")
            json.dump(self._parsed_data, f)
            f.close()

    def _load_parsed_data(self):
        self.input_id = self.get_id_by_url(self._url)
        if config.response_cache_dir is not None:
            dump_file_path = config.response_cache_dir.joinpath(
                "{}{}.json".format(self.get_filename_prefix(), self.input_id)
            )
            if dump_file_path.exists():
                f = dump_file_path.open("r")
                self._parsed_data = json.load(f)
                f.close()
                print("LOADED FROM DUMP")
                return self._parsed_data
        return None

    @staticmethod
    def get_id_by_url(URL: str):
        return URL.split('?')[0].split('/')[-1]

    @abc.abstractmethod
    def parseJSON(self, _type="images"):
        pass

    def get_data(self):
        data = self._load_parsed_data()
        if data is None:
            data = self.parseJSON()
            if config.response_cache_dir is not None:
                self._dump_parsed_data()
        return data

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

    @abc.abstractmethod
    def get_origin_name(self):
        pass

    def parseHTML(self, image_id) -> dict:
        """
        Parse tags by HTML page.
        :param image_id:
        :return: {"tag name 1": "tag category 1", …}
        """
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

    def get_auto_copyright_tags(self):
        return {"my little pony"}

    def tagIndex(self) -> dict:
        global indexed_tags
        taglist = self.getTagList()
        tags_parsed_data = None

        def tag_register(tag_name, tag_category, tag_alias, connection):
            tag_id = medialib_db.tags_indexer.check_tag_exists(tag_name, tag_category, connection)
            if tag_id is None:
                tag_id = medialib_db.tags_indexer.insert_new_tag(
                    tag_name, tag_category, tag_alias, connection
                )
            else:
                tag_id = tag_id[0]
            return tag_id


        artist = set()
        originalCharacter = set()
        indexed_characters = set()
        indexed_rating = set()
        indexed_species = set()
        indexed_content = set()
        indexed_set = set()
        indexed_copyright = self.get_auto_copyright_tags()

        for tag in taglist:
            if "oc:" in tag:
                _oc = tag.split(':')[1]
                originalCharacter.add(_oc)
                if config.use_medialib_db:
                    connection = medialib_db.common.make_connection()

                    tag_register(
                        _oc, "original character", "original character:{}".format(_oc), connection
                    )

                    connection.close()
            elif "artist:" in tag:
                _artist = tag.split(':')[1]
                artist.add(_artist)
                if config.use_medialib_db:
                    connection = medialib_db.common.make_connection()

                    tag_register(
                        _artist, "artist", tag, connection
                    )

                    connection.close()
            elif '.' in tag or '-' in tag:
                continue
            elif config.use_medialib_db:
                connection = medialib_db.common.make_connection()
                result: set = medialib_db.tags_indexer.get_category_of_tag(tag, connection)
                if result is None:
                    if tags_parsed_data is None:
                        tags_parsed_data = self.parseHTML(self.getID())
                    INDEXED_TAG_CATEGORY = {
                        "character": indexed_characters,
                        "rating": indexed_rating,
                        "species": indexed_species
                    }
                    if tags_parsed_data[tag] in INDEXED_TAG_CATEGORY:
                        category_name = tags_parsed_data[tag]
                        INDEXED_TAG_CATEGORY[tags_parsed_data[tag]].add(tag)
                    elif "comic:" in tag or "art pack:" in tag or "fanfic:" in tag:
                        category_name = "set"
                        indexed_set.add(tag)
                    else:
                        category_name = "content"
                        indexed_content.add(tag)
                    medialib_db.tags_indexer.insert_new_tag(
                        tag, category_name, tag, connection
                    )
                else:
                    INDEXED_TAG_CATEGORY = {
                        "rating": indexed_rating,
                        "character": indexed_characters,
                        "species": indexed_species,
                        "set": indexed_set,
                        "copyright": indexed_copyright,
                        "content": indexed_content
                    }
                    INDEXED_CATEGORIES = set(INDEXED_TAG_CATEGORY.keys())
                    presented_categories = result & INDEXED_CATEGORIES
                    if len(presented_categories):
                        selected_category = presented_categories.pop()
                        INDEXED_TAG_CATEGORY[selected_category].add(tag)
                    else:
                        print(tag, result)
                connection.close()
            else:
                if tag not in indexed_tags:
                    if tags_parsed_data is None:
                        tags_parsed_data = self.parseHTML(self.getID())
                    INDEXED_TAG_CATEGORY = {
                        "character": (characters, indexed_characters),
                        "rating": (rating, indexed_rating),
                        "species": (species, indexed_species)
                    }
                    if tags_parsed_data[tag] in INDEXED_TAG_CATEGORY:
                        INDEXED_TAG_CATEGORY[tags_parsed_data[tag]][0].add(tag)
                        INDEXED_TAG_CATEGORY[tags_parsed_data[tag]][1].add(tag)
                    else:
                        content.add(tag)
                        indexed_content.add(tag)
                    indexed_tags.add(tag)
                else:
                    INDEXED_TAG_CATEGORY = {
                        rating: indexed_rating,
                        characters: indexed_characters,
                        species: indexed_species,
                        content: indexed_content
                    }
                    for tag_category in INDEXED_TAG_CATEGORY:
                        if tag in tag_category:
                            INDEXED_TAG_CATEGORY[tag_category].add(tag)
        return {'artist': artist, 'original character': originalCharacter,
                'characters': indexed_characters, 'rating': indexed_rating,
                'species': indexed_species, 'content': indexed_content,
                'set': indexed_set, 'copyright': indexed_copyright}


    def file_deleted_handing(self, prefix, _id):
        logging.exception("deleted image {}".format(_id))
        if config.deleted_image_list_file_path is not None:
            deleted_list_f = pathlib.Path(config.deleted_image_list_file_path).open("a")
            parse_results = dict()
            try:
                parse_results = self.parseHTML(_id)
            except Exception as e:
                logger.exception("Some error was hapenned", e)
            deleted_list_f.write("{}{}: {}\n".format(
                prefix, _id, ", ".join([str(key) for key in parse_results.keys()])
            ))
            deleted_list_f.close()
        return 0, 0, 0, 0


    @abc.abstractmethod
    def verify_not_takedowned(self, data):
        pass

    @abc.abstractmethod
    def get_takedowned_content_info(self, data):
        pass

    @abc.abstractmethod
    def get_content_source_url(self, data):
        pass

    @abc.abstractmethod
    def get_output_filename(self, data, output_directory):
        pass

    @abc.abstractmethod
    def get_image_metadata(self, data):
        pass

    @abc.abstractmethod
    def get_image_format(self, data):
        pass

    @abc.abstractmethod
    def get_big_thumbnail_url(self, data):
        pass

    @abc.abstractmethod
    def get_raw_content_data(self):
        pass
