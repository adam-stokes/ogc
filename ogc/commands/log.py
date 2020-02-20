# pylint: disable=broad-except

import click

from ..collect import Collector
from .. import log


@click.option("--msg", metavar="<msg>", help="Log message")
@click.option("--level", metavar="<level>", help="Message level", default="INFO")
@click.command()
def cli(msg, level):
    if level == "INFO":
        log.info(msg)
    elif level == "DEBUG":
        log.debug(msg)
    else:
        log.info(msg)

def start():
    """
    Starts app
    """
    cli()
