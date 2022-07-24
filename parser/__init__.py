import re

import parser.tag_indexer
from . import Parser, derpibooru, ponybooru, twibooru, e621, furbooru, exceptions, tag_indexer


url_pattern = re.compile(r"https?://")
filename_prefix_pattern = re.compile(r"[a-z]{2}\d+")


def get_parser(url, use_medialib_db: bool):
    class_by_prefix = {
        derpibooru.FILENAME_PREFIX: derpibooru.DerpibooruParser,
        ponybooru.FILENAME_PREFIX: ponybooru.PonybooruParser,
        twibooru.FILENAME_PREFIX: twibooru.TwibooruParser,
        e621.FILENAME_PREFIX: e621.E621Parser,
        furbooru.FILENAME_PREFIX: furbooru.FurbooruParser
    }
    class_by_domain_name = {
        derpibooru.DerpibooruParser.get_domain_name_s(): derpibooru.DerpibooruParser,
        ponybooru.PonybooruParser.get_domain_name_s(): ponybooru.PonybooruParser,
        'twibooru.org': twibooru.TwibooruParser,
        e621.E621Parser.get_domain_name_s(): e621.E621Parser,
        furbooru.FurbooruParser.get_domain_name_s(): furbooru.FurbooruParser
    }
    raw_parser = None
    if url_pattern.match(url) is not None:
        for domain_name in class_by_domain_name:
            if domain_name in url:
                raw_parser = class_by_domain_name[domain_name](url)
        if raw_parser is None:
            raise exceptions.SiteNotSupported(url)
    elif filename_prefix_pattern.match(url) is not None:
        for prefix in class_by_prefix:
            if prefix in url:
                raw_parser = class_by_prefix[prefix](url[2:])
        if raw_parser is None:
            raise exceptions.NotBoorusPrefixError(url)
    else:
        raw_parser = derpibooru.DerpibooruParser(url)
    if use_medialib_db:
        return parser.tag_indexer.MedialibTagIndexer(raw_parser, url)
    else:
        return parser.tag_indexer.DefaultTagIndexer(raw_parser, url)

