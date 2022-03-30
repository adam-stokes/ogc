import sys

import click

from ogc import db
from ogc.log import Logger as log

from .base import cli


@click.command(help="Database migrations")
def db_migrate():
    log.info("Applying database migrations")
    db.migrate()


@click.command(help="Launches IPython REPL")
def shell():
    try:
        from IPython import embed
        from traitlets.config import get_config
    except ImportError:
        log.error(f"You need to have [underline]IPython[/] installed for this to work.")
        sys.exit(1)

    c = get_config()
    c.InteractiveShellEmbed.colors = "Linux"
    embed(config=c)

cli.add_command(db_migrate)
cli.add_command(shell)
