import sys

import click

from ogc import state
from ogc.actions import teardown

from ..provision import choose_provisioner
from .base import cli


@click.command(help="Destroys a node and its associated keys, storage, etc.")
@click.option("--name", multiple=True, required=True)
@click.option(
    "--force/--no-force",
    default=False,
    help="Force removal regardless of connectivity",
)
def rm(name, force):
    teardown(name, env=state.app.env, force=force)


@click.command(help="Destroys everything. Use with caution.")
@click.option(
    "--force/--no-force",
    default=False,
    help="Force removal regardless of connectivity",
)
def rm_all(force):
    teardown(env=state.app.env, force=force)


@click.option("--provider", default="aws", help="Provider to query")
@click.option("--filter", required=False, help="Filter by keypair name")
@click.command(help="Remove keypairs")
def rm_key_pairs(provider, filter):
    engine = choose_provisioner(provider, env=state.app.env)
    kps = []
    if filter:
        kps = [kp for kp in engine.list_key_pairs() if filter in kp.name]
    else:
        kps = [kp for kp in engine.list_key_pairs()]

    for kp in kps:
        click.secho(f"Removing keypair: {kp.name}", fg="green")
        engine.delete_key_pair(kp)


cli.add_command(rm)
cli.add_command(rm_all)
cli.add_command(rm_key_pairs)
