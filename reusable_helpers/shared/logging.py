import logging

from .config import UNSET, resolve


def get_logger(name: str, *, level=UNSET, format=UNSET) -> logging.Logger:
    level = resolve(level, env="LOG_LEVEL", default="INFO")
    format = resolve(
        format,
        env="LOG_FORMAT",
        default="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(format))
        logger.addHandler(handler)
    logger.propagate = False
    return logger
