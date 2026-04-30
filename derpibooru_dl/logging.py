import sys
import logging
import logging.handlers


def init(root_logger, application_name: str):
    console_logger = logging.StreamHandler(sys.stdout)
    console_logger.setLevel(logging.INFO)
    console_formater = logging.Formatter(
        "%(asctime)s::%(levelname)s::%(name)s::%(message)s", datefmt="%M:%S"
    )
    console_logger.setFormatter(console_formater)
    root_logger.addHandler(console_logger)

    file_rotating_handler = logging.handlers.RotatingFileHandler(
        filename="logs/{}.log".format(application_name),
        maxBytes=1_000_000,
        backupCount=5,
    )
    file_rotating_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s::%(process)dx%(thread)d::%(levelname)s::%(name)s::%(message)s"
    )
    file_rotating_handler.setFormatter(formatter)
    root_logger.addHandler(file_rotating_handler)

    root_logger.debug("Application {} started".format(application_name))
