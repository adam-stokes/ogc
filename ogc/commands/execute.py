""" Command to execute a spec
"""
import json
import sys

import click
from tabulate import tabulate

from ..spec import SpecConfigException, SpecProcessException
from ..state import app
from .base import cli


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
        app.log.info("No tasks found, please add phases and plugins to the specfile.")
        sys.exit(0)

    rows = [
        [
            plug.opt("description")
            if plug.opt("description")
            else "No description available.",
            plug.phase,
            ", ".join(sorted(plug.opt("tags"))) if plug.opt("tags") else "-",
        ]
        for plug in plugins
    ]
    click.echo(tabulate(rows, headers=["Task", "Phase", "Tags"]))
    click.echo("")
    click.echo("  Example:\n")
    click.echo("  > ogc execute --phase plan -t build-docs\n\n")


@click.command()
@click.option(
    "--phase", metavar="<phase>", required=False, help="Run a certain phase of the spec"
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
            click.secho(
                f"Cannot run {phase} phase, does not exist in this spec.",
                fg="red",
                bold=True,
            )
            sys.exit(1)

        plugins = [plugin for plugin in plugins_for_phase]

    if tag:
        if plugins:
            _plugins = plugins
        else:
            _plugins = []
            for _phase in app.phases.keys():
                plugins_for_phase = app.phases.get(_phase, None)
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
        for _phase in app.phases.keys():
            plugins_for_phase = app.phases.get(_phase, None)
            if plugins_for_phase:
                for plug in plugins_for_phase:
                    plugins.append(plug)

    app.log.info(f"Starting")
    for plugin in plugins:
        # Setup environment
        try:
            plugin.env()
        except SpecProcessException as error:
            click.secho(error, fg="red", bold=True)
            sys.exit(1)

        # Check for any option conflicts
        try:
            plugin.conflicts()
        except (SpecProcessException, SpecConfigException) as error:
            click.secho(error, fg="red", bold=True)
            sys.exit(1)

        # Execute the spec
        plugin.process()

    # save results
    app.collect.path.write_text(json.dumps(app.collect.db))
    if any(res["code"] > 0 for res in app.collect.db["results"]):
        click.secho("Errors when running tasks", fg="red", bold=True)
        app.log.debug("Errors:")
        for res in app.collect.db["results"]:
            if res["code"] > 0:
                msg = (
                    f"- Task: {res['description']}\n- Exit Code: {res['code']}\n"
                    f"- Reason:\n{res['output']}"
                )
                app.log.debug(msg)
                click.secho(msg, fg="red", bold=True)
        sys.exit(1)


cli.add_command(execute)
cli.add_command(tasks)
