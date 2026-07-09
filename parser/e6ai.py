import config
from .e621 import E621Parser

FILENAME_PREFIX = "ea"
ORIGIN = "e6ai"


class E6AIParser(E621Parser):
    @staticmethod
    def get_domain_name_s():
        return "e6ai.net"

    def get_filename_prefix(self):
        return FILENAME_PREFIX

    def get_origin_name(self):
        return ORIGIN

    def get_api_login(self):
        return config.e6ai_login

    def get_api_key(self):
        return config.e6ai_API_KEY
