""" Command to execute a spec
"""
import click
import sys
from .base import cli
from ..state import app
from ..spec import SpecProcessException, SpecConfigException
from ..enums import SPEC_PHASES


@click.command()
def tasks():
    """ Show tasks for a spec
    """
    plugins = []
    for phase in app.phases.keys():
            plugins_for_phase = app.phases.get(phase, None)
            if plugins_for_phase:
                for plug in plugins_for_phase:
                    plugins.append(plug)
    if not plugins:
        app.log.info('No tasks found, please add phases and plugins to the specfile.')
        sys.exit(0)

    click.echo("Tasks::\n")
    for plug in plugins:
        name = plug.metadata.get('__plugin_name__', plug.__class__.__name__)
        description = plug.opt('description') if plug.opt('description') else 'No description available.'
        tags = plug.opt('tags') if plug.opt('tags') else []
        if tags:
            tags = "-t ".join(tags)
        phase = plug.phase
        click.echo(f" - {name} :: {description}\n   Run Example:\n      > ogc execute --phase {phase} {tags}")

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
            _plugins = []
            for phase in app.phases.keys():
                plugins_for_phase = app.phases.get(phase, None)
                if plugins_for_phase:
                    for plug in plugins_for_phase:
                        _plugins.append(plug)

        plugins = [
            plugin
            for plugin in _plugins
            if "tags" in plugin.spec
            and set(plugin.get_plugin_option("tags")).intersection(tag)
        ]

    # no tags or phases specified, pull everything
    if not plugins:
        for phase in app.phases.keys():
            plugins_for_phase = app.phases.get(phase, None)
            if plugins_for_phase:
                for plug in plugins_for_phase:
                    plugins.append(plug)


    app.log.info(f"Validating tasks")
    for plugin in plugins:
        # Setup environment
        try:
            plugin.env()
        except SpecProcessException as error:
            app.log.error(error)
            sys.exit(1)

        # Check for any option conflicts
        try:
            plugin.conflicts()
        except (SpecProcessException, SpecConfigException) as error:
            app.log.error(error)
            sys.exit(1)

    app.log.info(f"Processing tasks")
    for plugin in plugins:
        # Execute the spec
        try:
            plugin.process()
        except SpecProcessException as error:
            app.log.error(error)
            sys.exit(1)


cli.add_command(execute)
cli.add_command(tasks)
