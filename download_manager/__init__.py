import logging

import config
import parser
from . import download_manager
from .file_downloader import FileDownloader
from .transcoder import TranscodeManager
from .download_manager import DownloadManager

logger = logging.getLogger(__name__)


def make_download_manager(_parser: parser.Parser.Parser):
    if config.do_transcode:
        return TranscodeManager(_parser)
    else:
        return FileDownloader(_parser)


def save_call(task: tuple[DownloadManager, str, dict, dict]) -> tuple[int, int, int, int]:
    logger.debug("task info (save call used): {}".format(task.__repr__()))
    return task[0].download(*task[1:])
