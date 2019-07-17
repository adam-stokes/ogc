""" Command to execute a spec
"""
import click
import sys
from .base import cli
from ..state import app
from ..spec import SpecProcessException, SpecConfigException


@click.command()
def execute():
    """ Execute loaded plugins
    """
    for plugin in app.plugins:
        app.log.debug(f"Processing > {plugin.NAME}")
        try:
            plugin.conflicts()
        except SpecConfigException as error:
            app.log.error(error)
            sys.exit(1)

        try:
            plugin.process()
        except SpecProcessException as error:
            app.log.error(error)
            sys.exit(1)


cli.add_command(execute)
