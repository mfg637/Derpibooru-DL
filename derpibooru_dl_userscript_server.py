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


class RouteFabric:
    def __init__(self, _parser):
        self._parser = _parser

    def handle(self):
        global error_message
        try:
            if error_message is not None:
                return error_message
            content = json.loads(flask.request.data.decode("utf-8"))
            parser = self._parser(content['imageId'])
            data = parser.parseJSON()
            parsed_tags = parser.tagIndex()
            out_dir = tagResponse.find_folder(parsed_tags)
            parser.dataValidator(data)
            parser.append2queue(output_directory=out_dir, data=data, tags=parsed_tags)
            return "OK"
        except Exception as e:
            error_message = traceback.format_exc()
            print(error_message)
            return error_message


@app.route('/', methods=['POST'])
def derpibooru_handler():
    fabric = RouteFabric(parser.derpibooru.DerpibooruParser)
    return fabric.handle()


@app.route('/twibooru', methods=['POST'])
def twibooru_handler():
    fabric = RouteFabric(parser.twibooru.TwibooruParser)
    return fabric.handle()


@app.route('/ponybooru', methods=['POST'])
def ponybooru_handler():
    fabric = RouteFabric(parser.ponybooru.PonybooruParser)
    return fabric.handle()


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
            parser.Parser.mysql_connection.close()
