import dataclasses
import enum
from psycopg2.extensions import connection as connection_type
from psycopg2.extensions import cursor as cursor_type


class TagCategory(enum.StrEnum):
    ARTIST = "artist"
    PROMPTER = "prompter"
    SET = "set"
    COPYRIGHT = "copyright"
    RATING = "rating"
    SPECIES = "species"
    CHARACTER = "character"
    CHARACTER_GROUP = "character-group"
    GENDER = "gender"
    COMIC = "comic"
    LORE = "lore"
    META = "meta"
    ERROR = "error"
    STYLE = "style"
    AI = "ai"
    CONTENT = "content"


@dataclasses.dataclass
class Tag:
    id: int
    name: str
    category: TagCategory

    def __init__(self, _id: int, name: str, category: TagCategory | str):
        self.id = _id
        self.name = name
        if isinstance(category, TagCategory):
            self.category = category
        elif type(category) is str:
            self.category = TagCategory(category)


def _get_tag_by_id(cursor: cursor_type, tag_id: int) -> Tag | None:
    sql_request = "SELECT * FROM tag WHERE ID = %s"
    cursor.execute(sql_request, (tag_id,))
    tag_raw_data = cursor.fetchone()
    if tag_raw_data is None:
        return None
    else:
        return Tag(*tag_raw_data)


def _get_tag_by_name_and_category(
    cursor: cursor_type, name: str, category: TagCategory | None
) -> Tag | None:
    sql_request = "SELECT * FROM tag WHERE name = %s and category = %s"
    cursor.execute(sql_request, (name, category))
    tag_raw_data = cursor.fetchone()
    if tag_raw_data is None:
        return None
    else:
        return Tag(*tag_raw_data)


def get_tag_by_id(connection: connection_type, tag_id: int) -> Tag | None:
    cursor = connection.cursor()
    result = _get_tag_by_id(cursor, tag_id)
    cursor.close()
    return result


def get_tag_by_name_and_category(
    connection: connection_type, name: str, category: TagCategory | None
) -> Tag | None:
    cursor = connection.cursor()
    result = _get_tag_by_name_and_category(cursor, name, category)
    cursor.close()
    return result


def _insert_tag(
    cursor: cursor_type, name: str, category: TagCategory
) -> int | None:
    sql_command = "INSERT INTO tag VALUES (DEFAULT, %s, %s) RETURNING id"
    cursor.execute(sql_command, (name, str(category)))
    tag_id = cursor.fetchone()
    if tag_id is None:
        return None
    else:
        return tag_id[0]


def add_tag(
    connection: connection_type, name: str, category: TagCategory
) -> int | None:
    """
    Creates new tag entry with given name and category and returns tag id.
    """
    cursor = connection.cursor()
    result = _insert_tag(cursor, name, category)
    cursor.close()
    connection.commit()
    return result


def get_or_create_tag_id(
    connection: connection_type, name: str, category: TagCategory
) -> int | None:
    cursor = connection.cursor()
    tag = _get_tag_by_name_and_category(cursor, name, category)
    if tag is not None:
        cursor.close()
        return tag.id
    else:
        tag_id = _insert_tag(cursor, name, category)
        cursor.close()
        connection.commit()
        return tag_id


def clear_table(connection: connection_type):
    sql_delete_command = "DELETE FROM tag"
    sql_reset_counter = "ALTER SEQUENCE tag_id_seq RESTART WITH 1"
    cursor = connection.cursor()
    cursor.execute(sql_delete_command, tuple())
    cursor.execute(sql_reset_counter, tuple())
    cursor.close()
    connection.commit()
