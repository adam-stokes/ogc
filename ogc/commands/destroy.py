import sys

import click

from ogc import actions, db
from ogc.log import Logger as log

from .base import cli


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
    nodes = actions.teardown_async(nodes=[node], force=force, only_db=only_db)
    with db.M.db.begin(db=db.M.nodes, write=True) as txn:
        for node in nodes:
            txn.delete(node.id.encode("ascii"))


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
def rm_all(force, only_db):
    nodes = db.get_nodes().unwrap_or_else(log.warning)
    if not nodes:
        sys.exit(1)

    results = actions.teardown_async(nodes=nodes, force=force, only_db=only_db)
    log.error("Failed to teardown all nodes") if not results else log.info(
        "Completed tearing down nodes, removing database entries."
    )

    with db.M.db.begin(db=db.M.nodes, write=True) as txn:
        for node in nodes:
            txn.delete(node.id.encode("ascii"))


cli.add_command(rm)
cli.add_command(rm_all)
