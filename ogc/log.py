""" log module
"""

import sys

import click
from loguru import logger

logger.remove()
logger.add(
    "ogc.log", rotation="500 MB", level="DEBUG"
)  # Automatically rotate too big file
logger.add(
    sys.stderr,
    colorize=True,
    format="{time:YYYY-MM-DD at HH:mm:ss} | <level>{level}</level> <green><b>{message}</b></green>",
    level="INFO",
)
logger.add(
    sys.stderr,
    colorize=True,
    format="{time:YYYY-MM-DD at HH:mm:ss} | <level>{level}</level> <red><b>{message}</b></red>",
    level="ERROR",
)


def debug(ctx):
    logger.debug(ctx)


def error(ctx):
    logger.error(ctx)


def info(ctx):
    logger.info(ctx)
