import threading

from . import Parser, derpibooru, ponybooru, twibooru


def get_parser(url):
    if derpibooru.DerpibooruParser.get_domain_name_s() in url:
        return derpibooru.DerpibooruParser(url)
    elif ponybooru.PonybooruParser.get_domain_name_s() in url:
        return ponybooru.PonybooruParser(url)
    elif 'twibooru.org' in url:
        return twibooru.TwibooruParser(url)
    else:
        return derpibooru.DerpibooruParser(url)

