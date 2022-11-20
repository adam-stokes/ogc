from __future__ import annotations

import sys

import click

from ogc.log import get_logger

from .base import cli

log = get_logger(__name__)


@click.command(help="Launches IPython REPL")
def shell() -> None:
    try:
        from IPython import embed
        from traitlets.config import get_config
    except ImportError:
        log.error("You need to have [underline]IPython[/] installed for this to work.")
        sys.exit(1)

    c = get_config()
    c.InteractiveShellEmbed.colors = "Linux"  # type: ignore
    embed(config=c)


cli.add_command(shell)
