import abc
from ..Parser import Parser
from ..e621 import E621Parser


class TagIndexer(Parser):
    """
    Decorates Parser object and adds tags indexing functionality.

    Parser needs tag indexer for their work, but it has two implementations (with database and without).
    Encapsulation MedialibTagIndexer allows to make dependency of "medialib-db" library optional.
    """
    def __init__(self, parser: Parser, url):
        super().__init__(url)
        self._parser = parser

    @abc.abstractmethod
    def index(self) -> dict:
        pass

    @abc.abstractmethod
    def e621_index(self) -> dict:
        pass

    def tagIndex(self) -> dict:
        if isinstance(self._parser, E621Parser):
            return self.e621_index()
        else:
            return self.index()

    # decorated methods
    def parseJSON(self, url=None, _type=None) -> dict:
        if _type is not None:
            return self._parser.parseJSON(url, _type)
        else:
            return self._parser.parseJSON(url)

    def parsehtml_get_image_route_name(self) -> str:
        return self._parser.parsehtml_get_image_route_name()

    def get_domain_name(self) -> str:
        return self._parser.get_domain_name()

    def getTagList(self) -> list:
        return self._parser.getTagList()

    def getID(self) -> str:
        return self._parser.getID()

    def dataValidator(self, data):
        return self._parser.dataValidator(data)

    def get_filename_prefix(self):
        return self._parser.get_filename_prefix()

    def get_origin_name(self):
        return self._parser.get_origin_name()

    def verify_not_takedowned(self, data):
        return self._parser.verify_not_takedowned(data)

    def get_takedowned_content_info(self, data):
        return self._parser.get_takedowned_content_info(data)

    def get_content_source_url(self, data):
        return self._parser.get_content_source_url(data)

    def get_output_filename(self, data, output_directory):
        return self._parser.get_output_filename(data, output_directory)

    def get_image_metadata(self, data):
        return self._parser.get_image_metadata(data)

    def get_image_format(self, data):
        return self._parser.get_image_format(data)

    def get_big_thumbnail_url(self, data):
        return self._parser.get_big_thumbnail_url(data)

    def get_raw_content_data(self):
        return self._parser.get_raw_content_data()
