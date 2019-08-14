""" Get plugin information
"""
import itertools
import os
import sys
import tempfile
from pathlib import Path

import click
import sh

from ..spec import SpecDepException
from ..state import app
from .base import cli


@click.command()
@click.option("--installable", is_flag=True)
def list_deps(installable):
    """ Show plugins dependency summary

    Example:

    > ogc --spec my-spec.yml list-deps

    Which can be automated with:

    > ogc --spec my-spec.yml list-deps --installable | sh -

    """
    show_only = False
    if not installable:
        show_only = True

    dep_cmds = []

    try:
        dep_cmds = [plugin.dep_check(show_only, installable) for plugin in app.plugins]
    except (TypeError, SpecDepException) as error:
        app.log.error(
            f"{error}: Does your spec have nested plugins more than 2 levels deep? That is currently unsupported."
        )
        sys.exit(1)

    dep_cmds = list(itertools.chain.from_iterable(dep_cmds))

    if not dep_cmds:
        app.log.info("No plugin dependencies listed.")
        sys.exit(0)

    if dep_cmds and show_only:
        app.log.info("Plugin dependency summary ::")

    for _dep in dep_cmds:
        if isinstance(_dep, str):
            app.log.info(f"- {_dep}")
        else:
            click.echo(_dep.install_cmd())


@click.command()
@click.argument("plugin")
def spec_doc(plugin):
    """ Show plugin documentation

    Example:

    > ogc --spec my-spec.toml spec-doc Runner
    """
    has_pandoc = sh.which("pandoc")
    if not any(_plugin.__class__.__name__ == plugin for _plugin in app.plugins):
        app.log.error(
            f"{plugin} is not listed in the referenced spec. Please see `list-plugins` for loaded plugins."
        )
        sys.exit(1)

    for _plugin in app.plugins:
        if _plugin.__class__.__name__ == plugin:
            output = "\n".join([_plugin.doc_render()])

            if has_pandoc:
                fp = tempfile.mkstemp()
                Path(fp[1]).write_text(output, encoding="utf8")
                click.echo(sh.pandoc(fp[1], "-s", "-f", "markdown", "-t", "plain"))
                os.close(fp[0])
            else:
                click.echo(output)
            return
    app.log.error(
        f"Could not find plugin {plugin}, make sure it's installed with `pip install --user ogc-plugins-{plugin.lower()}"
    )
    sys.exit(1)


@click.command()
def list_plugins():
    """ List all loaded plugins for spec

    Example:

    > ogc list-plugins
    """
    app.log.info("Plugins used:")
    _plugins = [
        _plugin.metadata.get("__plugin_name__", _plugin.__class__.__name__)
        for _plugin in app.plugins
    ]
    for _plugin in set(_plugins):
        app.log.info(f" -- {_plugin}")


cli.add_command(list_deps)
cli.add_command(list_plugins)
cli.add_command(spec_doc)
