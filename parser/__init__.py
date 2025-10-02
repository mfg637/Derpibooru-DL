import re

from . import (
    Parser,
    derpibooru,
    ponybooru,
    # Temporary disable these imageboards
    # Both of them requires additional changes
    twibooru,
    # e621,
    furbooru,
    tantabus,
    exceptions,
)


url_pattern = re.compile(r"https?://")
filename_prefix_pattern = re.compile(r"[a-z]{2}\d+")

class_by_prefix = {
    derpibooru.FILENAME_PREFIX: derpibooru.DerpibooruParser,
    ponybooru.FILENAME_PREFIX: ponybooru.PonybooruParser,
    twibooru.FILENAME_PREFIX: twibooru.TwibooruParser,
    # e621.FILENAME_PREFIX: e621.E621Parser,
    furbooru.FILENAME_PREFIX: furbooru.FurbooruParser,
    tantabus.FILENAME_PREFIX: tantabus.TantabusAIParser,
}

class_by_domain_name = {
    derpibooru.DerpibooruParser.get_domain_name_s(): derpibooru.DerpibooruParser,
    ponybooru.PonybooruParser.get_domain_name_s(): ponybooru.PonybooruParser,
    twibooru.TwibooruParser.get_domain_name_s(): twibooru.TwibooruParser,
    # e621.E621Parser.get_domain_name_s(): e621.E621Parser,
    furbooru.FurbooruParser.get_domain_name_s(): furbooru.FurbooruParser,
    tantabus.TantabusAIParser.get_domain_name_s(): tantabus.TantabusAIParser,
}


def get_parser(url):
    parser = None
    if url_pattern.match(url) is not None:
        for domain_name in class_by_domain_name:
            if domain_name in url:
                parser = class_by_domain_name[domain_name](url)
        if parser is None:
            raise exceptions.SiteNotSupported(url)
    elif filename_prefix_pattern.match(url) is not None:
        for prefix in class_by_prefix:
            if prefix in url:
                parser = class_by_prefix[prefix](url[2:])
        if parser is None:
            raise exceptions.NotBoorusPrefixError(url)
    else:
        parser = derpibooru.DerpibooruParser(url)
    return parser
