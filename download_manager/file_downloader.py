import logging
import pathlib
import config
from .download_manager import DownloadManager
import parser
from medialib_service import check_exists

logger = logging.getLogger(__name__)


class FileDownloader(DownloadManager):
    def __init__(self, _parser: parser.Parser):
        super().__init__(_parser)

    def _download_body(
        self,
        src_url: str,
        name: str,
        src_filename: pathlib.Path,
        output_directory: pathlib.Path,
        data: dict,
        tags: dict | None,
    ):
        if config.use_medialib and check_exists(
            self.parser.get_origin_name(), str(self.parser.get_content_id())
        ):
            self.skip_download = True
        elif self.is_rewriting_allowed() or not src_filename.is_file():
            if not config.simulate:
                self.download_file(src_filename, src_url)
        elif src_filename.is_file():
            self.skip_download = True
