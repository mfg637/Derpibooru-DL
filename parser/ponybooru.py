import json
import urllib.parse
import urllib.request
import config
import os
import re
import mysql.connector

from . import derpibooru


class PonybooruParser(derpibooru.DerpibooruParser):
    @staticmethod
    def get_domain_name_s():
        return 'ponybooru.org'

    @staticmethod
    def get_filename_prefix():
        return 'pb'

    def get_domain_name(self) -> str:
        return PonybooruParser.get_domain_name_s()