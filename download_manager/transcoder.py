import logging
import os
import pathlib

import PIL.Image

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

    def in_memory_transcode(
        self, src_url, name, output_directory, force_lossless=False
    ):
        source = self.do_binary_request(src_url)
        transcoder = pyimglib.transcoding.get_memory_transcoder(
            source,
            output_directory,
            name,
            force_lossless,
            self.is_rewriting_allowed()
        )
        return transcoder.transcode()

    def _simulate_transcode(self, original_format, large_image, src_filename, output_directory, name, src_url, force_lossless):
        if original_format in TRANSCODE_FILES:
            if self.is_rewriting_allowed() or not os.path.isfile(src_filename) and \
                    not pyimglib.transcoding.get_trancoded_file(
                        src_filename,
                        output_directory,
                        name
                    ):
                return 0, 0, 0, 0, None
            elif not pyimglib.transcoding.get_trancoded_file(src_filename, output_directory, name):
                return 0, 0, 0, 0, None
            elif config.enable_multiprocessing:
                return 0, 0, 0, 0, None
            else:
                return 0, 0, 0, 0, None
        else:
            if not os.path.isfile(src_filename):
                pass
            return 0, 0, 0, 0, src_filename

    def _do_transcode(
            self,
            original_format,
            large_image,
            src_filename: pathlib.Path,
            output_directory: pathlib.Path,
            name: str,
            src_url,
            force_lossless: bool
    ):
        if original_format in TRANSCODE_FILES:
            transcoded_file = pyimglib.transcoding.get_trancoded_file(
                        src_filename,
                        output_directory,
                        name
                    )
            if self.is_rewriting_allowed() or not os.path.isfile(src_filename) and \
                    transcoded_file is None:
                try:
                    return self.in_memory_transcode(src_url, name, output_directory, force_lossless)
                except PIL.Image.DecompressionBombError:
                    src_url = os.path.splitext(large_image)[0] + '.' + \
                        original_format
                    if 'https:' not in src_url:
                        src_url = 'https:' + src_url
                    return self.in_memory_transcode(src_url, name, output_directory, force_lossless)
            elif transcoded_file is None:
                transcoder = pyimglib.transcoding.get_file_transcoder(
                    src_filename, output_directory, name
                )
                if transcoder is not None:
                    return transcoder.transcode()
                else:
                    self.download_file(src_filename, src_url)
                    return 0, 0, 0, 0, src_filename
            elif config.enable_multiprocessing:
                self.skip_download = True
                if transcoded_file is not None:
                    return 0, 0, 0, 0, transcoded_file
                else:
                    return 0, 0, 0, 0, src_filename
        else:
            if not os.path.isfile(src_filename):
                self.download_file(src_filename, src_url)
            else:
                self.skip_download = True
            return 0, 0, 0, 0, src_filename

    def _download_body(
            self, src_url, name: str, src_filename: pathlib.Path, output_directory: pathlib.Path, data: dict, tags
    ):
        result = None

        force_lossless = 'vector' in tags['content']

        args = (
            self.parser.get_image_format(data),
            self.parser.get_big_thumbnail_url(data),
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
                result = self.parser.file_deleted_handing(self.parser.get_filename_prefix(), self.parser.getID())

        return result
