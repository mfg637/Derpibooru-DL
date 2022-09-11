import medialib_db
from .tag_indexer import TagIndexer


class MedialibTagIndexer(TagIndexer):
    @staticmethod
    def tag_register(tag_name, tag_category, tag_alias, connection):
        tag_id = medialib_db.tags_indexer.check_tag_exists(tag_name, tag_category, connection)
        if tag_id is None:
            tag_id = medialib_db.tags_indexer.insert_new_tag(
                tag_name, tag_category, tag_alias, connection
            )
        else:
            tag_id = tag_id[0]
        return tag_id

    def index(self):
        taglist = self._parser.getTagList()
        tags_parsed_data = None

        artist = set()
        originalCharacter = set()
        indexed_characters = set()
        indexed_rating = set()
        indexed_species = set()
        indexed_content = set()
        indexed_set = set()
        indexed_copyright = self._parser.get_auto_copyright_tags()

        for tag in taglist:
            if "oc:" in tag:
                tag_name = medialib_db.common.postgres_string_format(
                    tag.split(':')[1], medialib_db.common.TAG_TITLE_MAX_SIZE
                )
                originalCharacter.add(tag_name)

                connection = medialib_db.common.make_connection()
                MedialibTagIndexer.tag_register(
                    tag_name, "character", "character:{}".format(tag_name), connection
                )
                connection.close()
            elif "artist:" in tag:
                tag_name = medialib_db.common.postgres_string_format(
                    tag.split(':')[1], medialib_db.common.TAG_TITLE_MAX_SIZE
                )
                artist.add(tag_name)

                connection = medialib_db.common.make_connection()
                MedialibTagIndexer.tag_register(
                    tag_name, "artist", tag, connection
                )
                connection.close()
            #elif '.' in tag or '-' in tag:
            #    continue
            else:
                connection = medialib_db.common.make_connection()
                tag_name = medialib_db.common.postgres_string_format(
                    tag, medialib_db.common.TAG_TITLE_MAX_SIZE
                )
                result: set = medialib_db.tags_indexer.get_category_of_tag(tag, connection)
                if result is None:
                    if tags_parsed_data is None:
                        tags_parsed_data = self._parser.parseHTML(self._parser.getID())
                    INDEXED_TAG_CATEGORY = {
                        "character": indexed_characters,
                        "rating": indexed_rating,
                        "species": indexed_species
                    }
                    if tags_parsed_data[tag] in INDEXED_TAG_CATEGORY:
                        category_name = tags_parsed_data[tag]
                        INDEXED_TAG_CATEGORY[tags_parsed_data[tag]].add(tag_name)
                    elif tags_parsed_data[tag] == "content-fanmade" \
                            or "comic:" in tags_parsed_data[tag] \
                            or "art pack:" in tags_parsed_data[tag] \
                            or "fanfic:" in tags_parsed_data[tag]:
                        category_name = "set"
                        indexed_set.add(tag_name)
                    else:
                        category_name = "content"
                        indexed_content.add(tag_name)

                    if category_name == "character" and "oc:" not in tags_parsed_data[tag]:
                        tag_alias = "character:{}".format(tag_name)
                    else:
                        tag_alias = tag_name

                    medialib_db.tags_indexer.insert_new_tag(
                        tag_name, category_name, tag_alias, connection
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
                        INDEXED_TAG_CATEGORY[selected_category].add(tag_name)
                    else:
                        print(tag, tag_name, result)
                connection.close()
        return {'artist': artist, 'original character': originalCharacter,
                'characters': indexed_characters, 'rating': indexed_rating,
                'species': indexed_species, 'content': indexed_content,
                'set': indexed_set, 'copyright': indexed_copyright}

    def e621_index(self) -> dict:
        artist = set()
        originalCharacter = set()
        indexed_characters = set()
        indexed_rating = set()
        indexed_species = set()
        indexed_content = set()
        indexed_set = set()
        indexed_copyright = set()

        connection = medialib_db.common.make_connection()

        for tag in self._parser.get_raw_content_data()['tags']['copyright']:
            _tag = medialib_db.common.postgres_string_format(
                tag.replace("_", " "), medialib_db.common.TAG_TITLE_MAX_SIZE
            )
            indexed_copyright.add(_tag)

        for tag in self._parser.get_raw_content_data()['tags']['character']:
            _tag = tag
            if "_(mlp)" in tag:
                indexed_copyright.add("my little pony")
                _tag = tag.replace("_(mlp)", "")
            _tag = medialib_db.common.postgres_string_format(
                _tag.replace("_", " "), medialib_db.common.TAG_TITLE_MAX_SIZE
            )
            tag_alias = "character:{}".format(_tag)
            indexed_characters.add(_tag)
            MedialibTagIndexer.tag_register(
                _tag, 'character', tag_alias, connection
            )

        for tag in indexed_copyright:
            tag_alias = "copyright:{}".format(tag)
            MedialibTagIndexer.tag_register(
                tag, 'copyright', tag_alias, connection
            )

        for tag in self._parser.get_raw_content_data()['tags']['species']:
            indexed_species.add(medialib_db.common.postgres_string_format(
                tag.replace("_", " "), medialib_db.common.TAG_TITLE_MAX_SIZE
            ))

        for tag in self._parser.get_raw_content_data()['tags']['artist']:
            _tag = medialib_db.common.postgres_string_format(
                tag.replace("_", " "), medialib_db.common.TAG_TITLE_MAX_SIZE
            )
            artist.add(_tag)
            tag_alias = "{}:{}".format("artist", _tag)
            MedialibTagIndexer.tag_register(
                _tag, 'artist', tag_alias, connection
            )

        rating_table = {
            "s": "safe",
            "q": "questionable",
            "e": "explicit"
        }
        indexed_rating.add(rating_table[self._parser.get_raw_content_data()['rating']])
        MedialibTagIndexer.tag_register(
            rating_table[self._parser.get_raw_content_data()['rating']],
            'rating',
            rating_table[self._parser.get_raw_content_data()['rating']],
            connection
        )

        for tag in self._parser.get_raw_content_data()['tags']['general']:
            if tag == "anthro":
                indexed_species.add("anthro")
            else:
                _tag = medialib_db.common.postgres_string_format(
                    tag.replace("_", " "), medialib_db.common.TAG_TITLE_MAX_SIZE
                )
                indexed_content.add(_tag)
                MedialibTagIndexer.tag_register(
                    _tag, 'content', _tag, connection
                )

        for tag in indexed_species:
            MedialibTagIndexer.tag_register(
                tag, 'species', tag, connection
            )

        connection.close()

        return {'artist': artist, 'original character': originalCharacter,
                'characters': indexed_characters, 'rating': indexed_rating,
                'species': indexed_species, 'content': indexed_content,
                'set': indexed_set, 'copyright': indexed_copyright}
