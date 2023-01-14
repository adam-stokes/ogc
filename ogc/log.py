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


def log_missing_options(*args: str, **kwargs: str) -> bool:
    """Helper for setting required options on deployment operations"""
    _log = logging.getLogger("ogc")
    _missing_opts = []
    for arg in args:
        if arg not in kwargs:
            _missing_opts.append(f"{arg}=<needs_input>")
    if _missing_opts:
        _log.error(f"Missing required options to task: `-o {' '.join(_missing_opts)}`")
    return bool(len(_missing_opts) > 0)


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
