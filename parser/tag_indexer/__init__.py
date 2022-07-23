from .tag_indexer import TagIndexer
from .default_indexer import DefaultTagIndexer

try:
    import medialib_db
except ImportError:
    pass
else:
    from .medialib_indexer import MedialibTagIndexer
