import logging
import parser
import download_manager
import medialib_service
from . import tagResponse

logger = logging.getLogger(__name__)


def download(url, rewrite=False):
    try:
        _parser: parser.Parser.Parser = parser.get_parser(url)
    except parser.exceptions.NotBoorusPrefixError as e:
        logger.exception("invalid prefix in {}".format(e.url))
        exit(1)
    except parser.exceptions.SiteNotSupported as e:
        logger.exception("Site not supported {}".format(e.url))
        exit(1)
    try:
        data = _parser.get_data()
    except IndexError:
        exit(1)

    parsed_tags: dict = _parser.tags_processing()
    logger.debug("parsed tags: {}".format(parsed_tags.__repr__()))
    outdir = tagResponse.find_folder(parsed_tags)
    logger.info("output directory: {}".format(outdir))

    dm = download_manager.make_download_manager(_parser)
    if rewrite:
        dm.enable_rewriting()
    dm.download(outdir, data, parsed_tags)
    medialib_service.prepare_and_send_result(dm, parsed_tags, data, outdir)
