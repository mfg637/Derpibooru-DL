import dataclasses
import enum
import datetime
from psycopg2.extensions import connection as connection_type
from psycopg2.extensions import cursor as cursor_type


def check_image_exists(connection: connection_type, image_id: int) -> bool:
    cursor = connection.cursor()
    cursor.execute("SELECT count(*) FROM images where id = %s", (image_id,))
    result = cursor.fetchone()
    cursor.close()
    if result is None:
        raise ValueError("Unexpected None")
    return bool(result[0])


def check_duplicates(connection: connection_type, image_id: int) -> int | None:
    cursor = connection.cursor()
    cursor.execute(
        "SELECT target_id FROM image_duplicates where image_id = %s",
        (image_id,),
    )
    result = cursor.fetchone()
    if result is not None:
        result = result[0]
    cursor.close()
    return result


def _get_image_hidden(cursor: cursor_type, image_id: int):
    cursor.execute(
        "SELECT reason FROM image_hides WHERE image_id = %s",
        (image_id,),
    )
    is_hidden = cursor.fetchone()
    return is_hidden


def is_image_hidden(connection: connection_type, image_id: int) -> bool:
    cursor = connection.cursor()
    is_hidden = _get_image_hidden(cursor, image_id)
    cursor.close()
    return is_hidden is not None


@dataclasses.dataclass(frozen=True)
class Image:
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    image_width: int
    image_height: int
    image_size: int
    comment_count: int
    score: int
    favorites: int
    upvotes: int
    downvotes: int
    hides: int
    image_aspect_ration: float
    user_id: int | None
    hidden_from_users: bool
    image_mime_type: str
    image_format: str
    image_name: str
    version_path: str
    image_sha512_hash: str | None
    image_orig_sha512_hash: str | None
    description: str | None


def _get_image_by_id(cursor: cursor_type, image_id: int) -> Image | None:
    cursor.execute("SELECT * FROM images where id = %s", (image_id,))
    raw_result = cursor.fetchone()
    if raw_result is None:
        return None
    else:
        return Image(*raw_result)


def get_image_by_id(connection: connection_type, image_id: int) -> Image | None:
    cursor = connection.cursor()
    result = _get_image_by_id(cursor, image_id)
    cursor.close()
    return result


@dataclasses.dataclass(frozen=True)
class Tag:
    id: int
    image_count: int
    name: str
    slug: str
    category: str | None
    description: str | None
    short_description: str | None


def _get_tag_by_id(cursor: cursor_type, tag_id: int) -> Tag | None:
    sql_query = "SELECT * FROM tags WHERE id = %s"
    cursor.execute(sql_query, (tag_id,))
    raw_result = cursor.fetchone()
    if raw_result is None:
        return None
    else:
        return Tag(*raw_result)


def _get_tag_by_name(cursor: cursor_type, tag_name: str) -> Tag | None:
    sql_query = "SELECT * FROM tags WHERE name = %s"
    cursor.execute(sql_query, (tag_name,))
    raw_result = cursor.fetchone()
    if raw_result is None:
        return None
    else:
        return Tag(*raw_result)


def get_tag_by_id(connection: connection_type, tag_id: int) -> Tag | None:
    cursor = connection.cursor()
    result = _get_tag_by_id(cursor, tag_id)
    cursor.close()
    return result


def get_tag_by_name(connection: connection_type, tag_name: str) -> Tag | None:
    cursor = connection.cursor()
    result = _get_tag_by_name(cursor, tag_name)
    cursor.close()
    return result


def _get_tags_of_image(cursor: cursor_type, image_id: int) -> list[Tag]:
    sql_query = (
        "SELECT tags.* FROM image_taggings AS it INNER JOIN tags "
        "ON it.tag_id = tags.id "
        "WHERE it.image_id = %s"
    )
    cursor.execute(sql_query, (image_id,))
    raw_results = cursor.fetchall()
    results: list[Tag] = []
    for record in raw_results:
        results.append(Tag(*record))
    return results


def get_tags_of_image(connection: connection_type, image_id: int) -> list[Tag]:
    cursor = connection.cursor()
    results = _get_tags_of_image(cursor, image_id)
    cursor.close()
    return results


def simulate_image_api(
    connection: connection_type, image_id: int, cdn_domain_name="derpicdn.net"
):
    cursor = connection.cursor()
    is_hidden = _get_image_hidden(cursor, image_id)
    if is_hidden is not None:
        cursor.close()
        return {"image": {"id": image_id, "deletion_reason": is_hidden[0]}}
    image_data = _get_image_by_id(cursor, image_id)
    if image_data is None:
        raise ValueError()
    result = {
        "tags": [],
        "tag_ids": [],
        "representations": {},
        "id": image_id,
        "name": image_data.image_name,
        "width": image_data.image_width,
        "height": image_data.image_height,
        "view_url": "",
        "mime_type": image_data.image_mime_type,
        "format": image_data.image_format,
        "description": image_data.description,
        "__tags": None,
    }
    created_at: datetime.datetime = image_data.created_at
    result["view_url"] = "https://{}/img/view/{}/{}/{}/{}.{}".format(
        cdn_domain_name,
        created_at.year,
        created_at.month,
        created_at.day,
        image_id,
        image_data.image_format,
    )
    result["representations"]["full"] = result["view_url"]
    for repr_name in (
        "large",
        "medium",
        "small",
        "tall",
        "thumb",
        "thumb_small",
        "thumb_tiny",
    ):
        result["representations"][repr_name] = (
            "https://{}/img/{}/{}/{}/{}/{}.{}".format(
                cdn_domain_name,
                created_at.year,
                created_at.month,
                created_at.day,
                image_id,
                repr_name,
                image_data.image_format,
            )
        )
    tags: list[Tag] = _get_tags_of_image(cursor, image_id)
    result["__tags"] = tags
    for tag in tags:
        result["tags"].append(tag.name)
        result["tag_ids"].append(tag.id)
    cursor.close()
    return {"image": result}


def simulate_tag_api(connection: connection_type, tag_name: str) -> dict | None:
    cursor = connection.cursor()
    tag_info = _get_tag_by_name(cursor, tag_name)
    cursor.close()
    if tag_info is None:
        return None
    result = {
        "name": tag_info.name,
        "slug": tag_info.slug,
        "description": tag_info.description,
        "short_description": tag_info.short_description,
        "category": tag_info.category,
    }
    return {"tag": result}
