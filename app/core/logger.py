import logging
from logging.handlers import RotatingFileHandler
from app.core.config import settings


def setup_logger():
    logger = logging.getLogger("app")
    logger.setLevel(settings.LOG_LEVEL)

    formatter = logging.Formatter(settings.LOG_FORMAT)

    file_handler = RotatingFileHandler(
        "logs/app.log", maxBytes=1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    return logger


logger = setup_logger()
