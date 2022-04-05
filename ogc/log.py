""" log module
"""

import logging
from logging.handlers import TimedRotatingFileHandler

from rich.logging import RichHandler

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

cmdslog = TimedRotatingFileHandler("ogc.log", when="D", interval=1, backupCount=2)
cmdslog.setLevel(logging.INFO)
cmdslog.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

debuglog = TimedRotatingFileHandler(
    "ogc.debug.log", when="D", interval=1, backupCount=2
)
debuglog.setLevel(logging.DEBUG)
debuglog.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

Logger = logging.getLogger("ogc")
Logger.setLevel(logging.INFO)
Logger.addHandler(cmdslog)
Logger.addHandler(debuglog)
