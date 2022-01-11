import re
import exceptions

from . import Parser, derpibooru, ponybooru, twibooru, e621, furbooru

from .Parser import save_call


url_pattern = re.compile(r"https?://")
filename_prefix_pattern = re.compile(r"[a-z]{2}\d+")


def get_parser(url):
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
    if url_pattern.match(url) is not None:
        for domain_name in class_by_domain_name:
            if domain_name in url:
                return class_by_domain_name[domain_name](url)
        raise exceptions.SiteNotSupported(url)
    elif filename_prefix_pattern.match(url) is not None:
        for prefix in class_by_prefix:
            if prefix in url:
                return class_by_prefix[prefix](url[2:])
        raise exceptions.NotBoorusPrefixError(url)
    else:
        return derpibooru.DerpibooruParser(url)

