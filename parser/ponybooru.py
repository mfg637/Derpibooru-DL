FILENAME_PREFIX = 'pb'
ORIGIN = 'ponybooru'

from . import derpibooru


class PonybooruParser(derpibooru.DerpibooruParser):
    @staticmethod
    def get_domain_name_s():
        return 'ponybooru.org'

    def get_filename_prefix(self):
        return FILENAME_PREFIX

    def get_origin_name(self):
        return ORIGIN

    def get_domain_name(self) -> str:
        return PonybooruParser.get_domain_name_s()