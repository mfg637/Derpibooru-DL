from .tag_indexer import TagIndexer


indexed_tags = set()

characters = set()

rating = set()

species = set()

content = set()


class DefaultTagIndexer(TagIndexer):

    def e621_index(self) -> dict:
        return self.index()

    def index(self):
        global indexed_tags
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
                _oc = tag.split(':')[1]
                originalCharacter.add(_oc)

            elif "artist:" in tag:
                _artist = tag.split(':')[1]
                artist.add(_artist)
            elif '.' in tag or '-' in tag:
                continue
            else:
                if tag not in indexed_tags:
                    if tags_parsed_data is None:
                        tags_parsed_data = self._parser.parseHTML(self._parser.getID())
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
                        "rating": indexed_rating,
                        "characters": indexed_characters,
                        "species": indexed_species,
                        "content": indexed_content
                    }
                    for tag_category in INDEXED_TAG_CATEGORY:
                        if tag in tag_category:
                            INDEXED_TAG_CATEGORY[tag_category].add(tag)
        return {'artist': artist, 'original character': originalCharacter,
                'characters': indexed_characters, 'rating': indexed_rating,
                'species': indexed_species, 'content': indexed_content,
                'set': indexed_set, 'copyright': indexed_copyright}
