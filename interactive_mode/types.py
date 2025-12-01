import typing
import collections.abc
import abc
import re
import enum
import pathlib
import getpass
import urllib.parse


T = typing.TypeVar("T", covariant=False)

url_regex = re.compile(
    r"^([a-z]+:\/\/[a-zA-Z0-9\.]+)(:\d+)?(\/[\w\.]*)*(\?(([\w\-\[\]])+=([\w\-\%\.\+])+)?(\&[\w\-\[\]]+=[\w_\-\%\.\+]+)*)?\#?([\w\-]+)?$"
)
https_url_regex = re.compile(
    r"^(https:\/\/[a-zA-Z0-9\.]+)(:\d+)?(\/[\w\.]*)*(\?(([\w\-\[\]])+=([\w\-\%\.\+])+)?(\&[\w\-\[\]]+=[\w_\-\%\.\+]+)*)?\#?([\w\-]+)?$"
)


class MutableUserDefined:
    pass


Mutable = typing.Union[
    collections.abc.MutableMapping,
    collections.abc.MutableSequence,
    collections.abc.MutableSet,
    bytearray,
    MutableUserDefined,
]

Pointer = typing.Optional[Mutable]


class ArgumentType(abc.ABC, typing.Generic[T]):
    def __init__(self, type_label: str):
        self.type_label: str = type_label

    @abc.abstractmethod
    def parse_input(self, raw_value: str) -> T:
        pass

    def __str__(self):
        return self.type_label

    def input(self, prompt: typing.Optional[str] = None) -> str:
        if prompt is None:
            return input()
        else:
            return input(prompt)


class StringArgument(ArgumentType[str]):
    def __init__(self):
        super().__init__("str")

    def parse_input(self, raw_value: str):
        if type(raw_value) is str:
            return raw_value
        else:
            raise ValueError("Value is not string")


class PasswordArgument(StringArgument):
    def __init__(self, double_check: bool = False):
        super().__init__()
        self.type_label = "password"
        self.double_check = double_check

    def input(self, prompt: typing.Optional[str] = None) -> str:
        if prompt is None:
            value = getpass.getpass("")
            if self.double_check:
                value_check = getpass.getpass("(type again)")
                if value == value_check:
                    return value
                else:
                    raise ValueError("Passwords Mismatch")
            else:
                return value
        else:
            value = getpass.getpass(prompt)
            if self.double_check:
                print("Type password again.")
                value_check = getpass.getpass(prompt)
                if value == value_check:
                    return value
                else:
                    raise ValueError("Passwords Mismatch")
            else:
                return value


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


class StringEnumType(ArgumentType[str]):
    def __init__(self, enum_type: type[enum.StrEnum]):
        enum_elements: list[str] = []
        for enum_element in enum_type:
            enum_elements.append(str(enum_element))
        enum_str = ", ".join(enum_elements)
        super().__init__(f"str[{enum_str}]")
        self.enum_type = enum_type
        self._enum_str = enum_str

    def parse_input(self, raw_value: str):
        if type(raw_value) is str:
            if raw_value in self.enum_type:
                return raw_value
            else:
                raise ValueError(
                    f"Value {raw_value} not in set ({self._enum_str})"
                )
        else:
            raise ValueError("Value is not string")


class ExistingFilePath(ArgumentType[pathlib.Path]):
    def __init__(self):
        super().__init__("Path")

    def parse_input(self, raw_value: str):
        path = pathlib.Path(raw_value)
        if path.exists():
            return path
        else:
            raise ValueError("File path is not exists")


true_literal_strings: set[str] = {"True", "true", "t", "yes", "y", "Yes", "Y"}
false_listeral_strings: set[str] = {"False", "false", "f", "no", "n", "No", "N"}


class BooleanType(ArgumentType[bool]):
    def __init__(self):
        super().__init__("bool")

    def parse_input(self, raw_value: str):
        if raw_value in true_literal_strings:
            return True
        elif raw_value in false_listeral_strings:
            return False
        else:
            raise ValueError("Value is not true or false literal")
