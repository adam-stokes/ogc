""" Command to execute a spec
"""
import click
from .base import cli
from ..state import app


@click.command()
def execute():
    """ Execute loaded plugins
    """
    for plugin in app.plugins:
        plugin.process()
    return


cli.add_command(execute)
