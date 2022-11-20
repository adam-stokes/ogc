""" log module
"""

from __future__ import annotations

import logging
import os
import typing as t

import rich.console
from rich.logging import RichHandler

_LOGGER_INITIALIZED = False


class Logger(logging.Logger):
    ...  # pragma: nocover


def get_logger(name: str) -> Logger:
    """
    Get a `logging.Logger` instance
    """
    global _LOGGER_INITIALIZED

    if not _LOGGER_INITIALIZED:
        _LOGGER_INITIALIZED = True

        log_level = os.environ.get("OGC_LOG_LEVEL", "").upper()
        if log_level in ("DEBUG", "TRACE"):
            logger = logging.getLogger("ogc")
            logger.setLevel(logging.DEBUG if log_level == "DEBUG" else "INFO")
            handler = RichHandler(
                rich_tracebacks=True, omit_repeated_times=False, show_time=False
            )
            logger.addHandler(handler)

    logger = logging.getLogger(name)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sh").setLevel(logging.WARNING)

    return t.cast(Logger, logger)


CONSOLE = rich.console.Console(log_time=True)
