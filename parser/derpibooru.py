import datetime
import json
import logging
import os
import pathlib
import re
import time
import urllib.parse
import urllib.request

import psycopg2

import medialib_db
from .Parser import FileTypes

logger = logging.getLogger(__name__)

import requests

from . import Parser


FILENAME_PREFIX = 'db'
ORIGIN = 'derpibooru'

def make_connection():
    try:
        return psycopg2.connect(
            host="localhost",
            database="derpibooru",
            user=medialib_db.config.db_user,
            password=medialib_db.config.db_password
        )
    except psycopg2.OperationalError:
        return None


class DerpibooruParser(Parser.Parser):
    def identify_filetype(self) -> FileTypes:
        filetype = Parser.Parser.identify_by_mimetype(self.get_data()["image"]["mime_type"])
        if filetype == FileTypes.IMAGE and "animated" in self.get_data()['image']['tags']:
            filetype = FileTypes.ANIMATION
        return filetype

    def get_origin_name(self):
        return ORIGIN

    def getID(self) -> str:
        try:
            return str(self.get_data()['image']["id"])
        except KeyError as e:
            print(self.get_data())
            raise e

    def getTagList(self) -> list:
        return self.get_data()['image']['tags']

    def parsehtml_get_image_route_name(self) -> str:
        return 'images'

    def get_domain_name(self) -> str:
        return DerpibooruParser.get_domain_name_s()

    @staticmethod
    def get_domain_name_s():
        return 'derpibooru.org'

    def get_filename_prefix(self):
        return FILENAME_PREFIX

    def parseJSON(self, url=None, _type="images", trial_count=2) -> dict:
        def check_exists(content_id, connection):
            cursor = connection.cursor()
            cursor.execute(
                "SELECT id FROM images where id = %s",
                (content_id,)
            )
            result = cursor.fetchone() is not None
            cursor.close()
            return result

        def check_duplicates(content_id, connection):
            cursor = connection.cursor()
            cursor.execute(
                "SELECT target_id FROM image_duplicates where image_id = %s",
                (content_id,)
            )
            result = cursor.fetchone()
            if result is not None:
                result = result[0]
            cursor.close()
            return result

        def generate_data(content_id, connection):
            cursor = connection.cursor()
            cursor.execute(
                "SELECT reason FROM image_hides WHERE image_id = %s",
                (content_id,)
            )
            is_hided = cursor.fetchone()
            if is_hided is not None:
                cursor.close()
                return {"image":{"id": content_id, "deletion_reason": is_hided[0]}}
            cursor.execute(
                "SELECT * FROM images where id = %s",
                (content_id,)
            )
            raw_result = cursor.fetchone()
            if raw_result is None:
                raise ValueError()
            result = {
                "tags": [],
                "representations": {},
                "id": content_id,
                "name": raw_result[17],
                "width": raw_result[3],
                "height": raw_result[4],
                "view_url": "",
                "mime_type": raw_result[15],
                "format": raw_result[16],
                "description": raw_result[21]
            }
            created_at: datetime.datetime = raw_result[1]
            result["view_url"] = "https://derpicdn.net/img/view/{}/{}/{}/{}.{}".format(
                created_at.year,
                created_at.month,
                created_at.day,
                content_id,
                raw_result[16]
            )
            result["representations"]["full"] = result["view_url"]
            for repr_name in ("large", "medium", "small", "tall", "thumb", "thumb_small", "thumb_tiny"):
                result["representations"][repr_name] = "https://derpicdn.net/img/{}/{}/{}/{}/{}.{}".format(
                    created_at.year,
                    created_at.month,
                    created_at.day,
                    content_id,
                    repr_name,
                    raw_result[16]
                )
            cursor.execute(
                "SELECT tag_id FROM image_taggings where image_id = %s",
                (content_id,)
            )
            tag_ids = cursor.fetchall()
            for tag_id_row in tag_ids:
                tag_id = tag_id_row[0]
                cursor.execute(
                    "SELECT name FROM tags where id = %s",
                    (tag_id,)
                )
                tag_name = cursor.fetchone()[0]
                result["tags"].append(tag_name)
            cursor.close()
            return {"image": result}

        id = None
        if url is not None:
            id = url
        else:
            id = self.get_id_by_url(self._url)
        data = None
        if self.get_origin_name() == ORIGIN:
            db_local_instance = make_connection()
            if db_local_instance is not None:
                content_founded = check_exists(id, db_local_instance)
                duplicate_of = check_duplicates(id, db_local_instance)
                if duplicate_of is not None:
                    logger.info("duplicate founded")
                    data = self.parseJSON(duplicate_of)
                elif content_founded:
                    logger.info("content_founded")
                    data = generate_data(id, db_local_instance)
                db_local_instance.close()
        if data is None:
            request_url = 'https://{}/api/v1/json/{}/{}'.format(self.get_domain_name_s(), _type, urllib.parse.quote(str(id)))
            logger.debug("url: {}".format(url))
            logger.info("parseJSON: {}".format(request_url))
            try:
                request_data = requests.get(request_url)
            except Exception as e:
                print(e)
                return
            data = None
            if request_data.status_code == 404:
                raise IndexError("not founded \"{}\"".format(url))
            try:
                data = request_data.json()
            except json.JSONDecodeError as e:
                if trial_count > 0:
                    logger.warning("JSON decode error. HTTP status code:{} Raw data: \n{}".format(
                        request_data.status_code, request_data.text))
                    print("try again after 10 minutes")
                    time.sleep(600)
                    return self.parseJSON(url, _type, trial_count - 1)
                else:
                    logger.error("JSON decode error. HTTP status code:{} Raw data: \n{}".format(
                        request_data.status_code, request_data.text))
                    raise e
            while "duplicate_of" in data["image"] and data["image"]["duplicate_of"] is not None:
                data = self.parseJSON(str(data["image"]["duplicate_of"]))
        if 'tags' not in data['image']:
            data['image']['tags'] = []
        self._parsed_data = data
        return data

    def dataValidator(self, data):
        if 'image' not in data:
            raise KeyError("data has no \'image\'")
        data = data['image']
        if 'representations' not in data:
            raise KeyError("data has no \'representations\'")
        if 'full' not in data['representations']:
            raise KeyError("not found full representation")
        if type(data['representations']['full']) is not str:
            raise TypeError(
                "data['representations']['full'] is not str: "+data['representations']['full'].__class__.__name__
            )
        if type(os.path.splitext(data['representations']['full'])) is not tuple:
            raise TypeError(
                "os.path.splitext(data['representations']['full']) is not tuple: " + \
                os.path.splitext(data['representations']['full']).__class__.__name__
            )
        if type(os.path.splitext(data['representations']['full'])[0]) is not str:
            raise TypeError(
                "os.path.splitext(data['representations']['full'])[0] is not str: " + \
                os.path.splitext(data['representations']['full'])[0].__class__.__name__
            )
        if 'format' not in data:
            raise KeyError("data has no format property")
        if type(data["format"]) is not str:
            raise TypeError(
                "data[\"format\"] is not str: "+data["format"].__class__.__name__
            )
        if 'large' not in data['representations']:
            raise KeyError("not found large representation")

    def check_is_takedowned(self, data):
        return 'deletion_reason' in data['image'] and data['image']['deletion_reason'] is not None

    def get_takedowned_content_info(self, data):
        return self.file_deleted_handing(FILENAME_PREFIX, data['image']['id'])

    def get_content_source_url(self, data):
        return os.path.splitext(data['image']['representations']['full'])[0] + '.' + data['image']["format"].lower()

    def get_output_filename(self, data, output_directory: pathlib.Path) -> tuple[str, pathlib.Path]:
        data = data['image']
        name = ''
        if 'name' in data and data['name'] is not None:
            name = "{}{} {}".format(
                self.get_filename_prefix(),
                data["id"],
                re.sub('[/\[\]:;|=*".?]', '', os.path.splitext(data["name"])[0])
            )
        else:
            name = "{}{}".format(self.get_filename_prefix(), data["id"])
        return name, output_directory.joinpath("{}.{}".format(name, data["format"].lower()))

    def get_image_metadata(self, data):
        return {
            "title": data['image']['name'],
            "origin": self.get_origin_name(),
            "id": data['image']["id"]
        }

    def get_image_format(self, data):
        return data['image']['format']

    def get_big_thumbnail_url(self, data):
        return data['image']['representations']["large"]

    def get_raw_content_data(self):
        return self.get_data()['image']
