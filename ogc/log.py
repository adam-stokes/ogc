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


def get_logger(name: str, verbose: bool = False) -> Logger:
    """
    Get a `logging.Logger` instance
    """
    global _LOGGER_INITIALIZED

    # if verbose is passed, remove existing logger and reinitialize
    if verbose and _LOGGER_INITIALIZED:
        for hndl in logging.getLogger("ogc").handlers:
            logging.getLogger("ogc").removeHandler(hndl)
        os.environ["OGC_LOG_LEVEL"] = "DEBUG"
        _LOGGER_INITIALIZED = False

    if not _LOGGER_INITIALIZED:
        _LOGGER_INITIALIZED = True

        log_level = os.environ.get("OGC_LOG_LEVEL", "").upper()
        logger = logging.getLogger("ogc")
        logger.setLevel(logging.DEBUG if log_level == "DEBUG" else logging.INFO)
        handler = RichHandler(
            rich_tracebacks=True,
            omit_repeated_times=False,
            show_time=True,
            log_time_format="[%H:%M:%S]",
            tracebacks_show_locals=True if log_level == "DEBUG" else False,
            tracebacks_suppress=["click"],
            show_level=True,
            console=CONSOLE,
        )

        logger.addHandler(handler)

    logger = logging.getLogger(name)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sh").setLevel(logging.WARNING)

    return t.cast(Logger, logger)


CONSOLE = rich.console.Console(log_time=True)
