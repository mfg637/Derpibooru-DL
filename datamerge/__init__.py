import logging
import pathlib
import flask
import random
import string
import parser
import config
import medialib_db
import PIL.Image

import pyimglib
from derpibooru_dl import tagResponse

logger = logging.getLogger(__name__)

random_chars = list(string.ascii_letters + string.digits)

datamerge_blueprint = flask.Blueprint('data_merge', __name__, url_prefix='/merge')

@datamerge_blueprint.route("/form")
def show_form():
    return flask.render_template("merge-form.html")

def submit_in_database(
    outname: pathlib.Path, data, src_file_name, file_type, origin_name, tags, image_hash, origin_id, description, connection
):
    _name = None
    media_type = None
    if 'name' in data:
        _name = data['name']
    else:
        _name = src_file_name
    if outname is not None:
        if file_type in {parser.Parser.FileTypes.IMAGE, parser.Parser.FileTypes.VECTOR_IMAGE}:
            media_type = "image"
        elif file_type == parser.Parser.FileTypes.ANIMATION:
            media_type = "video-loop"
        elif file_type == parser.Parser.FileTypes.VIDEO:
            media_type = "video"
        else:
            media_type = "image"
        _description = None
        content_id = None
        if "description" is not None and len(description):
            _description = description
        try:
            content_id = medialib_db.srs_indexer.register(
                pathlib.Path(outname),
                _name,
                media_type,
                _description,
                origin_name,
                origin_id,
                tags,
                connection
            )
        except Exception as e:
            logger.exception(
                "Exception at content id={} from {}".format(data["id"], origin_name)
            )
            raise e
        if content_id is not None and image_hash is not None:
            medialib_db.set_image_hash(content_id, image_hash, connection)
        return content_id

def pick_parser_class(url):
    raw_parser = None
    parser_request_url = None
    if parser.url_pattern.match(url) is not None:
        parser_request_url = url
        for domain_name in parser.class_by_domain_name:
            if domain_name in url:
                raw_parser = parser.class_by_domain_name[domain_name]
        if raw_parser is None:
            raise parser.exceptions.SiteNotSupported(url)
    elif parser.filename_prefix_pattern.match(url) is not None:
        parser_request_url = url[2:]
        for prefix in parser.class_by_prefix:
            if prefix in url:
                raw_parser = parser.class_by_prefix[prefix]
        if raw_parser is None:
            raise parser.exceptions.NotBoorusPrefixError(url)
    else:
        parser_request_url = url
        raw_parser = parser.derpibooru.DerpibooruParser
    return raw_parser, parser_request_url

@datamerge_blueprint.route("handle", methods=['POST'])
def handle_content():
    logging.info("start handling request")
    file = flask.request.files['content_file']
    content_url = flask.request.form['origin']
    new_file_name = "".join(random.choices(list(string.ascii_letters + string.digits), k=16))
    old_file_name = file.filename
    if old_file_name == '':
        flask.abort(422, "empty file name")
    new_file_name = new_file_name + pathlib.PurePath(old_file_name).suffix
    parser_class, parser_url = pick_parser_class(content_url)
    if parser_class == parser.e621.E621Parser:
        _parser = parser.tag_indexer.decorate(parser_class, config.use_medialib_db, parser_url)
        data = _parser.parseJSON()
        parsed_tags = _parser.tagIndex()
        out_dir = pathlib.Path(tagResponse.find_folder(parsed_tags))
        out_dir.mkdir(parents=True, exist_ok=True)
        file_path = out_dir.joinpath(new_file_name)
        file_type = parser.Parser.Parser.identify_by_mimetype(file.mimetype)
        logger.info(f"saving file: {file_path}")
        file.save(file_path)
        image_hash = None
        if file_type == parser.Parser.FileTypes.IMAGE:
            with PIL.Image.open(file_path) as img:
                image_hash = pyimglib.calc_image_hash(img)
        content_id = None
        origin_id = data["post"]["id"]
        description = None
        if "description" in data["post"]:
            description = data["post"]["description"]
        if config.use_medialib_db:
            connection = medialib_db.common.make_connection()
            content_id = submit_in_database(
                file_path,
                data,
                old_file_name,
                file_type,
                "e621",
                parsed_tags,
                image_hash,
                origin_id,
                description,
                connection
            )
            connection.close()
        return (
            f"file name: {old_file_name}<br>"
            f"parsed tags: {parsed_tags.__repr__()}<br>"
            f"out_dir: {out_dir}<br>"
            f"new file name: {new_file_name}<br>"
            f"origin id: {origin_id}<br>"
            f"content_id: {content_id}"
        )
    else:
        flask.abort(500, "Not implemented")

