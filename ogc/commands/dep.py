""" Get plugin information
"""
import click
import sys
import sh
import tempfile
import os
from pathlib import Path
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
            app.log.error(
                f"{error}: Does your spec have nested plugins more than 2 levels deep? That is currently unsupported."
            )
            sys.exit(1)


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

    > ogc --spec my-spec.toml list-plugins
    """
    for _plugin in app.plugins:
        app.log.info(f" -- {_plugin.__class__.__name__}")
    return


cli.add_command(plugin_deps)
cli.add_command(list_plugins)
cli.add_command(spec_doc)
