import dataclasses
import enum
from psycopg2.extensions import connection as connection_type
from psycopg2.extensions import cursor as cursor_type
import datetime
from . import tag as tag_module


class OriginNameType(enum.StrEnum):
    DERPIBOORU = "derpibooru"
    PONYBOORU = "ponybooru"
    FURBOORU = "furbooru"
    TANTABUS = "tantabus"
    TWIBOORU = "twibooru"
    E621 = "e621"


@dataclasses.dataclass(frozen=True)
class OriginTag:
    origin_name: OriginNameType
    tag_name: str
    tag_slug: str | None
    description: str | None
    short_description: str | None
    category: str | None
    tag_id: int
    last_update: datetime.datetime | None


class OriginTagBuilder:
    def __init__(self):
        self.origin_name: OriginNameType | None = None
        self.tag_name: str | None = None
        self.tag_slug: str | None = None
        self.description: str | None = None
        self.short_description: str | None = None
        self.category: str | None = None
        self.tag_id: int | None = None
        self.last_update: datetime.datetime | None = None

    def build(self) -> OriginTag:
        if not isinstance(self.origin_name, OriginNameType):
            raise TypeError(
                "OriginTagBuilder.origin_name is not OriginNameType"
            )
        if type(self.tag_name) is not str:
            raise TypeError("OriginTagBuilder.tag_name is not string")
        if not (type(self.tag_slug) is str or self.tag_slug is None):
            raise TypeError("OriginTagBuilder.tag_slug must be string or None")
        if not (type(self.description) is str or self.description is None):
            raise TypeError(
                "OriginTagBuilder.description must be string or None"
            )
        if not (
            type(self.short_description) is str
            or self.short_description is None
        ):
            raise TypeError(
                "OriginTagBuilder.short_description must be string or None"
            )
        if not (type(self.category) is str or self.category is None):
            raise TypeError("OriginTagBuilder.category must be string or None")
        if type(self.tag_id) is not int:
            raise TypeError("OriginTagBuilder.tag_id is not an integer")
        if not (
            isinstance(self.last_update, datetime.datetime)
            or self.last_update is None
        ):
            raise TypeError(
                "OriginTagBuilder.last_update must be datetime or None"
            )
        return OriginTag(
            self.origin_name,
            self.tag_name,
            self.tag_slug,
            self.description,
            self.short_description,
            self.category,
            self.tag_id,
            self.last_update,
        )


def _get_by_tag_id(cursor: cursor_type, tag_id: int) -> list[OriginTag]:
    sql_command = "SELECT * FROM origin_tag WHERE tag_id = %s"
    cursor.execute(sql_command, (tag_id,))
    raw_results = cursor.fetchall()
    results: list[OriginTag] = []
    for row in raw_results:
        results.append(OriginTag(OriginNameType(row[0]), *row[1:]))
    return results


def get_by_tag_id(connection: connection_type, tag_id: int) -> list[OriginTag]:
    cursor = connection.cursor()
    results = _get_by_tag_id(cursor, tag_id)
    cursor.close()
    return results


def _get_by_tag_name(
    cursor: cursor_type, origin: OriginNameType, tag_name: str
) -> OriginTag | None:
    sql_command = (
        "SELECT * FROM origin_tag " "WHERE origin_name = %s AND tag_name = %s"
    )
    cursor.execute(sql_command, (str(origin), tag_name))
    result = cursor.fetchone()
    if result is None:
        return None
    else:
        return OriginTag(OriginNameType(result[0]), *result[1:])


def get_by_tag_name(
    connection: connection_type, origin: OriginNameType, tag_name: str
) -> OriginTag | None:
    cursor = connection.cursor()
    result = _get_by_tag_name(cursor, origin, tag_name)
    cursor.close()
    return result


def _insert(cursor: cursor_type, origin_tag: OriginTag):
    existing_tag = tag_module._get_tag_by_id(cursor, origin_tag.tag_id)
    if existing_tag is None:
        raise ValueError(f"Tag with ID = {origin_tag.tag_id} does not exists")
    if origin_tag.last_update is None:
        sql_command = "INSERT INTO origin_tag VALUES (%s, %s, %s, %s, %s, %s, %s, DEFAULT)"
        cursor.execute(
            sql_command,
            (
                str(origin_tag.origin_name),
                origin_tag.tag_name,
                origin_tag.tag_slug,
                origin_tag.description,
                origin_tag.short_description,
                origin_tag.category,
                origin_tag.tag_id,
            ),
        )
    else:
        sql_command = (
            "INSERT INTO origin_tag VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        )
        cursor.execute(
            sql_command,
            (
                str(origin_tag.origin_name),
                origin_tag.tag_name,
                origin_tag.tag_slug,
                origin_tag.description,
                origin_tag.short_description,
                origin_tag.category,
                origin_tag.tag_id,
                origin_tag.last_update,
            ),
        )


def add_origin_tag(connection: connection_type, origin_tag: OriginTag):
    cursor = connection.cursor()
    _insert(cursor, origin_tag)
    cursor.close()
    connection.commit()


def add_if_not_exists(connection: connection_type, origin_tag: OriginTag):
    cursor = connection.cursor()
    existing_tag = _get_by_tag_name(
        cursor, origin_tag.origin_name, origin_tag.tag_name
    )
    if existing_tag is None:
        _insert(cursor, origin_tag)
        cursor.close()
        connection.commit()
    else:
        cursor.close()


def clear_table(connection: connection_type):
    cursor = connection.cursor()
    cursor.execute("DELETE FROM origin_tag", tuple())
    cursor.close()
    connection.commit()
