""" Command to execute a spec
"""
import click
import sys
from .base import cli
from ..state import app
from ..spec import SpecDepException


@click.command()
@click.option("--installable", is_flag=True)
def plugin_deps(installable):
    """ Show plugins dependency summary

    Example:

    > ogc --spec my-spec.toml plugin-deps

    Which can be automated with:

    > ogc --spec my-spec.toml plugin-deps --installable | sh -

    """
    show_only = False
    if not installable:
        show_only = True

    if show_only:
        click.echo("Plugin dependency summary ::\n")

    for plugin in app.plugins:
        try:
            plugin.dep_check(show_only, installable)
        except (TypeError, SpecDepException) as error:
            app.log.error(f"{error}: Does your spec have nested plugins more than 2 levels deep? That is currently unsupported.")
            sys.exit(1)

cli.add_command(plugin_deps)
