""" log module
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

import rich.console
from rich.logging import RichHandler

LOGFORMAT_RICH = "%(message)s"
LOGFORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

handler = RichHandler(
    rich_tracebacks=True,
    omit_repeated_times=False,
    show_time=True,
    log_time_format="[%X]",
    tracebacks_show_locals=False,
    tracebacks_suppress=["click", "httpx", "sh"],
    show_level=True,
    show_path=False,
    enable_link_path=False,
)
handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
handler.setLevel(os.environ.get("OGC_LOG_LEVEL", logging.INFO))

OGC_DEBUG_FILE = os.environ.get("OGC_DEBUG_FILE", "ogc-debug.log")
rfd = RotatingFileHandler(
    OGC_DEBUG_FILE, maxBytes=1024 * 1024 * 10, backupCount=10  # 10Mb
)
rfd.setLevel(logging.DEBUG)
rfd.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

logging.basicConfig(
    level=logging.NOTSET,
    handlers=[
        handler,
        rfd,
    ],
)
CONSOLE = rich.console.Console(log_time=True)
