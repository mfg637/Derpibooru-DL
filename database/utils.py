import config
import enum
import psycopg2
import psycopg2.extensions


class DatabaseEnum(enum.Enum):
    APP_PROD = enum.auto()
    APP_TEST = enum.auto()
    DERPIBOORU = enum.auto()


def make_connection(
    database: DatabaseEnum = DatabaseEnum.APP_PROD,
) -> psycopg2.extensions.connection:
    if database is DatabaseEnum.APP_PROD:
        return psycopg2.connect(
            host=config.app_db_host,
            database=config.app_db_prod,
            user=config.db_user,
            password=config.db_password,
        )
    elif database is DatabaseEnum.APP_TEST:
        return psycopg2.connect(
            host=config.app_db_host,
            database=config.app_db_test,
            user=config.db_user,
            password=config.db_password,
        )
    elif database is DatabaseEnum.DERPIBOORU:
        return psycopg2.connect(
            host=config.derpibooru_dump_db_host,
            database="derpibooru",
            user=config.derpibooru_dump_db_user,
            password=config.derpibooru_dump_db_password,
        )
    else:
        raise ValueError(f"Unknown database: {database.__repr__()}")


def sanitize_string(input_str: str | None) -> str | None:
    if input_str is None:
        return None
    return str(input_str).replace("\x00", "")


def get_value_or_fail(
    db_record: tuple | None, error_message: str | Exception, _index: int = 0
):
    """
    Retrieve a value from a database record tuple
    or raise an error if the record is None.

    Args:
        db_record (tuple[T] | None):
            The database record as a tuple, or None if not found.
        error_message (str | Exception):
            The error message or Exception to raise if db_record is None.
        _index (int, optional):
            The index of the value to retrieve from the tuple. Defaults to 0.

    Returns:
        T: The value at the specified index in the db_record tuple.

    Raises:
        Exception: If db_record is None and error_message is a string.
        Exception: If db_record is None
            and error_message is an Exception instance (raises it directly).
    """
    if db_record is not None:
        return db_record[_index]
    else:
        if isinstance(error_message, Exception):
            raise error_message
        else:
            raise Exception(error_message)
