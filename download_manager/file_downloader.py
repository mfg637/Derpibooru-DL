import logging
import os

import config
from .download_manager import DownloadManager
import parser

logger = logging.getLogger(__name__)


class FileDownloader(DownloadManager):
    def __init__(self, _parser: parser.Parser):
        super().__init__(_parser)

    def _download_body(self, src_url, name, src_filename, output_directory: str, data: dict, tags):
        if self.is_rewriting_allowed() or not os.path.isfile(src_filename):
            if not config.simulate:
                self.download_file(src_filename, src_url)
                return 0, 0, 0, 0, src_filename

