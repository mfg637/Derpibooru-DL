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
    def get_domain_name():
        return 'ponybooru.org'

    @staticmethod
    def get_filename_prefix():
        return 'pb'