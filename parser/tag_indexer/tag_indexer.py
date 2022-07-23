import abc
from ..Parser import Parser


class TagIndexer(abc.ABC):
    def __init__(self, parser: Parser):
        self._parser = parser

    @abc.abstractmethod
    def index(self) -> dict:
        pass

    @abc.abstractmethod
    def e621_index(self) -> dict:
        pass
