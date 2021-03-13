#!/usr/bin/python3
# -*- coding: utf-8 -*-

import flask
import json
import traceback

import config
import parser
from derpibooru_dl import tagResponse

app = flask.Flask(__name__)
error_message = None


@app.route('/', methods=['POST'])
def derpibooru_handler():
    global error_message
    try:
        if error_message is not None:
            return error_message
        content = json.loads(flask.request.data.decode("utf-8"))
        derpibooru_parser = parser.derpibooru.DerpibooruParser(content['imageId'])
        data = derpibooru_parser.parseJSON()
        parsed_tags = derpibooru_parser.tagIndex()
        out_dir = tagResponse.find_folder(parsed_tags)
        derpibooru_parser.append2queue(output_directory=out_dir, data=data, tags=parsed_tags)
        return "OK"
    except Exception as e:
        #error_message = "{}: {}".format(e.__class__.__name__, str(e))
        error_message = traceback.format_exc()
        print(error_message)
        return error_message


if __name__ == '__main__':
    try:
        app.run(host="localhost", port=5757)
    except Exception as e:
        error_message = traceback.format_exc()
        print(error_message)
    finally:
        if config.enable_images_optimisations:
            import derpibooru_dl.imgOptimizer
            derpibooru_dl.imgOptimizer.printStats()
        if config.use_mysql:
            parser.derpibooru.mysql_connection.close()
