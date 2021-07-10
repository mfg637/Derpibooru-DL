import threading

from . import Parser, derpibooru, ponybooru, twibooru


def get_parser(url):
    if derpibooru.DerpibooruParser.get_domain_name_s() in url:
        return derpibooru.DerpibooruParser(url)
    elif derpibooru.FILENAME_PREFIX in url:
        return derpibooru.DerpibooruParser(url[2:])
    elif ponybooru.PonybooruParser.get_domain_name_s() in url:
        return ponybooru.PonybooruParser(url)
    elif ponybooru.FILENAME_PREFIX in url:
        return ponybooru.PonybooruParser(url[2:])
    elif 'twibooru.org' in url:
        return twibooru.TwibooruParser(url)
    elif twibooru.FILENAME_PREFIX in url:
        return twibooru.TwibooruParser(url[2:])
    else:
        return derpibooru.DerpibooruParser(url)

