from . import derpibooru

FILENAME_PREFIX = 'ta'
ORIGIN = 'tantabus'


class TantabusAIParser(derpibooru.DerpibooruParser):
    @staticmethod
    def get_domain_name_s():
        return 'tantabus.ai'

    def get_filename_prefix(self):
        return FILENAME_PREFIX

    def get_origin_name(self):
        return ORIGIN

    def get_domain_name(self) -> str:
        return TantabusAIParser.get_domain_name_s()