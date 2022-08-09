import logging
import os

import config
import parser
from .download_manager import DownloadManager

logger = logging.getLogger(__name__)

if config.do_transcode:
    import pyimglib
    import pyimglib.transcoding
    from PIL.Image import DecompressionBombError

TRANSCODE_FILES = {'png', 'jpg', 'jpeg', 'gif', 'webm'}


class TranscodeManager(DownloadManager):
    def __init__(self, _parser: parser.Parser.Parser):
        super().__init__(_parser)

    def _simulate_transcode(self, original_format, large_image, src_filename, output_directory, name, src_url, force_lossless):
        if original_format in TRANSCODE_FILES:
            if self.enable_rewriting() or not os.path.isfile(src_filename) and \
                    not pyimglib.transcoding.check_exists(
                        src_filename,
                        output_directory,
                        name
                    ):
                return 0, 0, 0, 0, None
            elif not pyimglib.transcoding.check_exists(src_filename, output_directory, name):
                return 0, 0, 0, 0, None
            elif config.enable_multiprocessing:
                return 0, 0, 0, 0, None
            else:
                return 0, 0, 0, 0, None
        else:
            if not os.path.isfile(src_filename):
                pass
            return 0, 0, 0, 0, src_filename

    def _do_transcode(self, original_format, large_image, src_filename, output_directory, name, src_url, force_lossless):
        if original_format in TRANSCODE_FILES:
            if self.enable_rewriting() or not os.path.isfile(src_filename) and \
                    not pyimglib.transcoding.check_exists(
                        src_filename,
                        output_directory,
                        name
                    ):
                try:
                    return self.in_memory_transcode(src_url, name, output_directory, force_lossless)
                except DecompressionBombError:
                    src_url = \
                        'https:' + os.path.splitext(large_image)[0] + '.' + \
                        original_format
                    return self.in_memory_transcode(src_url, name, output_directory, force_lossless)
            elif not pyimglib.transcoding.check_exists(src_filename, output_directory, name):
                transcoder = pyimglib.transcoding.get_file_transcoder(
                    src_filename, output_directory, name
                )
                if transcoder is not None:
                    transcoder.transcode()
                else:
                    self.download_file(src_filename, src_url)
            elif config.enable_multiprocessing:
                return 0, 0, 0, 0, None
        else:
            if not os.path.isfile(src_filename):
                self.download_file(src_filename, src_url)
            return 0, 0, 0, 0, src_filename

    def _download_body(self, src_url, name, src_filename, output_directory: str, data: dict, tags):
        result = None

        force_lossless = 'vector' in tags['content']

        args = (
            self._parser.get_image_format(data),
            self._parser.get_big_thumbnail_url(data),
            src_filename,
            output_directory,
            name,
            src_url,
            force_lossless
        )
        if config.simulate:
            self._simulate_transcode(*args)
        else:
            try:
                result = self._do_transcode(*args)
            except pyimglib.exceptions.NotIdentifiedFileFormat:
                result = self._parser.file_deleted_handing(self._parser.get_filename_prefix(), self._parser.getID())

        return result
