import click

from ogc import actions, db, state

from ..provision import choose_provisioner
from .base import cli

if not state.app.engine:
    state.app.engine = db.connect()
    state.app.session = db.session(state.app.engine)


@click.command(help="Destroys a node and its associated keys, storage, etc.")
@click.option("--name", multiple=True, required=True)
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
def rm(name, force, only_db):
    actions.teardown_async(name, force=force, only_db=only_db)


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
    with state.app.session as session:
        names = [node.instance_name for node in session.query(db.Node).all()]
        actions.teardown_async(names, force=force, only_db=only_db)


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
