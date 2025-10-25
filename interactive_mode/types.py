import typing
import abc
import re
import urllib.parse


T = typing.TypeVar("T", covariant=False)

url_regex = re.compile(
    r"^([a-z]+:\/\/[a-zA-Z0-9\.]+)(:\d+)?(\/[\w\.]*)*(\?(([\w\-\[\]])+=([\w\-\%\.\+])+)?(\&[\w\-\[\]]+=[\w_\-\%\.\+]+)*)?\#?([\w\-]+)?$"
)
https_url_regex = re.compile(
    r"^(https:\/\/[a-zA-Z0-9\.]+)(:\d+)?(\/[\w\.]*)*(\?(([\w\-\[\]])+=([\w\-\%\.\+])+)?(\&[\w\-\[\]]+=[\w_\-\%\.\+]+)*)?\#?([\w\-]+)?$"
)


class ArgumentType(abc.ABC, typing.Generic[T]):
    def __init__(self, type_label: str):
        self.type_label: str = type_label

    @abc.abstractmethod
    def parse_input(self, raw_value: str) -> T:
        pass

    def __str__(self):
        return self.type_label


class StringArgument(ArgumentType[str]):
    def __init__(self):
        super().__init__("str")

    def parse_input(self, raw_value: str):
        return raw_value


class IntegerArgument(ArgumentType[int]):
    def __init__(self):
        super().__init__("int")

    def parse_input(self, raw_value: str):
        return int(raw_value)


class UrlType(ArgumentType[urllib.parse.ParseResult]):
    def __init__(self):
        super().__init__("url")

    def parse_input(self, raw_value: str):
        match = url_regex.fullmatch(raw_value)
        if match is None:
            raise ValueError("Value is not URL")
        else:
            return urllib.parse.urlparse(raw_value)


class UrlString(ArgumentType[str]):
    def __init__(self):
        super().__init__("url")

    def parse_input(self, raw_value: str):
        match = url_regex.fullmatch(raw_value)
        if match is None:
            raise ValueError("Value is not URL")
        else:
            return urllib.parse.urlunparse(urllib.parse.urlparse(raw_value))


class HttpsUrlType(ArgumentType[urllib.parse.ParseResult]):
    def __init__(self):
        super().__init__("url[https]")

    def parse_input(self, raw_value: str):
        match = https_url_regex.fullmatch(raw_value)
        if match is None:
            raise ValueError("Value is not URL")
        else:
            return urllib.parse.urlparse(raw_value)


class HttpsUrlString(ArgumentType[str]):
    def __init__(self):
        super().__init__("url[https]")

    def parse_input(self, raw_value: str):
        match = https_url_regex.fullmatch(raw_value)
        if match is None:
            raise ValueError("Value is not URL")
        else:
            return urllib.parse.urlunparse(urllib.parse.urlparse(raw_value))
