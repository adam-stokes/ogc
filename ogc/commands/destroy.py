from __future__ import annotations

import sys

import click

from ogc import actions, db
from ogc.log import CONSOLE as con
from ogc.log import get_logger

from .base import cli

log = get_logger(__name__)


@click.command(help="Destroys a node and its associated keys, storage, etc.")
@click.option(
    "--by-name",
    required=False,
    help="Remove node by its Name",
)
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
def rm(by_name: str, force: bool, only_db: bool) -> None:
    node = db.get_node(by_name).unwrap_or_else(log.warning)
    if not node:
        sys.exit(1)
    actions.teardown_async(nodes=[node], force=force, only_db=only_db)


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
def rm_all(force: bool, only_db: bool) -> None:
    nodes = db.get_nodes().unwrap_or_else(log.warning)
    if not nodes:
        sys.exit(1)

    results = actions.teardown_async(nodes=nodes, force=force, only_db=only_db)
    log.error("Failed to teardown all nodes") if not results else con.log(
        "Completed tearing down nodes"
    )


cli.add_command(rm)
cli.add_command(rm_all)
