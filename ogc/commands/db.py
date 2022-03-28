import sys
from pathlib import Path

import click
from rich.console import Console

import alembic.command
import alembic.config

from .base import cli

console = Console()


@click.command(help="Database Operations")
def db_migrate():
    # retrieves the directory that *this* file is in
    migrations_dir = Path(__file__).parent.parent.parent / 'alembic'
    # this assumes the alembic.ini is also contained in this same directory
    config_file = migrations_dir.parent / "alembic.ini"

    config = alembic.config.Config(file_=str(config_file))
    config.set_main_option("script_location", str(migrations_dir))

    # upgrade the database to the latest revision
    alembic.command.upgrade(config, "head")

@click.command(help="Launch database shell")
def db_shell():
    try:
        from IPython import embed
        from traitlets.config import get_config
    except ImportError:
        console.log(f"You need to have IPython installed for this to work.")
        sys.exit(1)

    c = get_config()
    c.InteractiveShellEmbed.colors = "Linux"
    embed(config=c)

cli.add_command(db_migrate)
cli.add_command(db_shell)
