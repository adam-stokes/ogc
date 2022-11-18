""" log module
"""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler

from rich.logging import RichHandler

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

cmdslog = TimedRotatingFileHandler("ogc.log", when="W0", interval=1, backupCount=2)
cmdslog.setLevel(logging.DEBUG)
cmdslog.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

Logger = logging.getLogger("ogc")
Logger.setLevel(logging.INFO)
Logger.addHandler(cmdslog)
