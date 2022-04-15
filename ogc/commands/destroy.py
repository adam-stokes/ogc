import sys

import click

from ogc import actions, db, state
from ogc.log import Logger as log

from ..provision import choose_provisioner
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
def rm(by_name, force, only_db):
    result = actions.teardown_async(by_name, force=force, only_db=only_db)
    if result.is_err():
        state.app.log.error(result.err())
        sys.exit(1)


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
    user = db.get_user().unwrap_or_else(log.critical)
    if not user:
        sys.exit(1)

    results = actions.teardown_async(
        nodes=user.nodes, config=user, force=force, only_db=only_db
    )
    log.error("Failed to teardown all nodes") if not results else log.info(
        "Completed tearing down nodes."
    )
    log.info("Removing database entries")

    for node in results:
        if node in user.nodes:
            print(node)

    with db.get().begin(write=True) as txn:
        txn.put(user.slug.encode("ascii"), db.model_as_pickle(user))


@click.option("--provider", default="aws", help="Provider to query")
@click.option("--filter", required=False, help="Filter by keypair name")
@click.command(help="Remove keypairs")
def rm_key_pairs(provider, filter):
    engine = choose_provisioner(provider, env=state.app.env)
    kps = []
    if filter:
        kps = [kp for kp in engine.list_key_pairs() if filter in kp.name]
    else:
        kps = list(engine.list_key_pairs())

    for kp in kps:
        click.secho(f"Removing keypair: {kp.name}", fg="green")
        engine.delete_key_pair(kp)


cli.add_command(rm)
cli.add_command(rm_all)
cli.add_command(rm_key_pairs)
