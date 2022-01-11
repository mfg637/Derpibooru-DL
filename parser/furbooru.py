from . import derpibooru

FILENAME_PREFIX = 'fb'
ORIGIN = 'furbooru'


class FurbooruParser(derpibooru.DerpibooruParser):
    @staticmethod
    def get_domain_name_s():
        return 'furbooru.org'

    def get_filename_prefix(self):
        return FILENAME_PREFIX

    def get_origin_name(self):
        return ORIGIN

    def get_domain_name(self) -> str:
        return FurbooruParser.get_domain_name_s()

    def get_auto_copyright_tags(self):
        return set()
