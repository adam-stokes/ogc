""" Command to execute a spec
"""
import click
import sys
from .base import cli
from ..state import app
from ..spec import SpecProcessException, SpecConfigException


@click.command()
@click.option(
    "-t",
    "--tag",
    metavar="<tag>",
    required=False,
    multiple=True,
    help="Only run specific plugin(s) which matches a tag",
)
def execute(tag):
    """ Execute OGC Specification
    """

    if tag:
        app.plugins = [
            plugin
            for plugin in app.plugins
            if "tags" in plugin.spec
            and set(plugin.get_plugin_option("tags")).intersection(tag)
        ]

    for plugin in app.plugins:
        # Setup environment
        try:
            app.log.info(f"Setup Environment > {plugin.friendly_name}")
            plugin.env()
        except SpecProcessException as error:
            app.log.error(error)
            sys.exit(1)

    for plugin in app.plugins:
        # Check for any option conflicts
        try:
            app.log.info(f"Checking conflicts > {plugin.friendly_name}")
            plugin.conflicts()
        except (SpecProcessException, SpecConfigException) as error:
            app.log.error(error)
            sys.exit(1)

    for plugin in app.plugins:
        # Execute the spec
        try:
            app.log.info(f"Processing > {plugin.friendly_name}")
            plugin.process()
        except SpecProcessException as error:
            app.log.error(error)
            sys.exit(1)


cli.add_command(execute)
