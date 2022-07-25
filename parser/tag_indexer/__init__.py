from .tag_indexer import TagIndexer
from .default_indexer import DefaultTagIndexer
from ..Parser import Parser
import logging

logger = logging.getLogger(__name__)

medialib_db_usable = False
try:
    import medialib_db
except ImportError:
    pass
else:
    medialib_db_usable = True
    from .medialib_indexer import MedialibTagIndexer


def decorate(parser_type: Parser, use_medialib_db: bool, url):
    logger.debug("parser type: {}, url: {}".format(parser_type, url))
    if use_medialib_db and medialib_db_usable:
        return MedialibTagIndexer(parser_type(url), url)
    else:
        return DefaultTagIndexer(parser_type(url), url)
