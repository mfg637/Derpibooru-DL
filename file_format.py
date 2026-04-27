import enum
from pathlib import Path
from io import BytesIO


class FormatEnum(enum.StrEnum):
    PNG = "PNG"
    JPEG = "JPEG"
    GIF = "GIF"
    MPEG_4 = "MPEG 4"
    WEBP = "WEBP"
    WEBM = "WEBM"
    AVIF = "AVIF"
    SVG = "SVG"
    MOV = "MOV"


FILE_SUFFIX_TO_FORMAT: dict[str, FormatEnum] = {
    ".png": FormatEnum.PNG,
    ".jpg": FormatEnum.JPEG,
    ".jpeg": FormatEnum.JPEG,
    ".jfif": FormatEnum.JPEG,
    ".gif": FormatEnum.GIF,
    ".mp4": FormatEnum.MPEG_4,
    ".m4v": FormatEnum.MPEG_4,
    ".webp": FormatEnum.WEBP,
    ".webm": FormatEnum.WEBM,
    ".avif": FormatEnum.AVIF,
    ".svg": FormatEnum.SVG,
    ".mov": FormatEnum.MOV,
}

FILE_FORMAT_DEFAULT_SUFFIX: dict[FormatEnum, str] = {
    FormatEnum.PNG: ".png",
    FormatEnum.JPEG: ".jpeg",
    FormatEnum.GIF: ".gif",
    FormatEnum.MPEG_4: ".mp4",
    FormatEnum.WEBP: ".webp",
    FormatEnum.WEBM: ".webm",
    FormatEnum.AVIF: ".avif",
    FormatEnum.SVG: ".svg",
    FormatEnum.MOV: ".mov",
}

MIME_TYPE_BY_FORMAT: dict[FormatEnum, str] = {
    FormatEnum.PNG: "image/png",
    FormatEnum.JPEG: "image/jpeg",
    FormatEnum.GIF: "image/gif",
    FormatEnum.MPEG_4: "video/mp4",
    FormatEnum.WEBP: "image/webp",
    FormatEnum.WEBM: "video/webm",
    FormatEnum.AVIF: "image/avif",
    FormatEnum.SVG: "image/svg+xml",
    FormatEnum.MOV: "video/quicktime",
}

MIME_TYPE_TO_FORMAT: dict[str, FormatEnum] = {
    value: key for key, value in MIME_TYPE_BY_FORMAT.items()
}

EXTENSIONS_BY_MIME: dict[str, str] = {
    mime: FILE_FORMAT_DEFAULT_SUFFIX[MIME_TYPE_TO_FORMAT[mime]]
    for mime in MIME_TYPE_TO_FORMAT
}
MIME_BY_EXTENSION: dict[str, str] = {
    ext: MIME_TYPE_BY_FORMAT[_fmt]
    for ext, _fmt in FILE_SUFFIX_TO_FORMAT.items()
}

GENERIC_BINARY_FILE_MIME = "application/octet-stream"


def is_png(file: str | Path | BytesIO) -> bool:
    """
    Checks if a file is a valid PNG by inspecting its 8-byte magic header.
    """
    PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

    if isinstance(file, BytesIO):
        header = file.read(8)
        return header == PNG_MAGIC
    try:
        with open(file, "rb") as f:
            header = f.read(8)
            return header == PNG_MAGIC
    except IOError, FileNotFoundError:
        return False


class MediaTypes(enum.Enum):
    IMAGE = enum.auto()
    VECTOR_IMAGE = enum.auto()
    ANIMATION = enum.auto()
    VIDEO = enum.auto()


FILE_EXTENSION_ASSOCIATION: dict[str, MediaTypes] = {
    "jpg": MediaTypes.IMAGE,
    "jpeg": MediaTypes.IMAGE,
    "png": MediaTypes.IMAGE,
    "gif": MediaTypes.ANIMATION,
    "webm": MediaTypes.VIDEO,
    "webp": MediaTypes.VIDEO,
    "mp4": MediaTypes.VIDEO,
}
