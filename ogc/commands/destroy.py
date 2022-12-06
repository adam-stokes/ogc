from __future__ import annotations

import sys
from pathlib import Path

import click
from dotenv import load_dotenv

import ogc.loader
from ogc.log import CONSOLE, get_logger
from ogc.signals import ready_teardown

from .base import cli

log = get_logger("ogc")


@click.command(help="Destroys everything. Use with caution.")
@click.option(
    "--force/--no-force",
    default=False,
    help="Force removal regardless of connectivity",
)
@click.option(
    "--only-db/--no-only-db",
    default=False,
    help="Force removal of database records only",
)
@click.argument("spec", type=Path)
def rm_all(force: bool, only_db: bool, spec: Path) -> None:
    """Destroy all nodes"""
    load_dotenv()
    if not ogc.loader.from_path(spec):
        log.error(f"Could not load {spec} into OGC.")
        sys.exit(1)
    with CONSOLE.status("Destroy machines", spinner="aesthetic"):
        ready_teardown.send(dict(force=force, only_db=only_db))


cli.add_command(rm_all)
