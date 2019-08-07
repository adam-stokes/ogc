""" Command to execute a spec
"""
import click
import sys
from .base import cli
from ..state import app
from ..spec import SpecProcessException, SpecConfigException
from ..enums import SPEC_PHASES


@click.command()
@click.option(
    "--phase",
    metavar="<phase>",
    required=False,
    help="Run a certain phase of the spec",
)
@click.option(
    "-t",
    "--tag",
    metavar="<tag>",
    required=False,
    multiple=True,
    help="Only run specific plugin(s) which matches a tag",
)
def execute(phase, tag):
    """ Execute OGC Specification
    """

    plugins = []
    if phase:
        plugins_for_phase = app.phases.get(phase, None)
        if not plugins_for_phase:
            app.log.error(f'Cannot run {phase} phase, does not exist in this spec.')
            sys.exit(1)

        plugins = [
            plugin
            for plugin in plugins_for_phase
        ]

    if tag:
        if plugins:
            _plugins = plugins
        else:
            _plugins = [
                app.phases[phase]
                for phase in app.phases.keys()
                if app.phases.get(phase, None)
            ]

        plugins = [
            plugin
            for plugin in _plugins
            if "tags" in plugin.spec
            and set(plugin.get_plugin_option("tags")).intersection(tag)
        ]

    for plugin in plugins:
        # Setup environment
        try:
            app.log.info(f"{plugin.phase} :: {plugin.friendly_name} : Setup Environment")
            plugin.env()
        except SpecProcessException as error:
            app.log.error(error)
            sys.exit(1)

    for plugin in plugins:
        # Check for any option conflicts
        try:
            app.log.info(f"{plugin.phase} :: {plugin.friendly_name} : Checking conflicts")
            plugin.conflicts()
        except (SpecProcessException, SpecConfigException) as error:
            app.log.error(error)
            sys.exit(1)

    for plugin in plugins:
        # Execute the spec
        try:
            app.log.info(f"{plugin.phase} :: {plugin.friendly_name} : Processing")
            plugin.process()
        except SpecProcessException as error:
            app.log.error(error)
            sys.exit(1)


cli.add_command(execute)
