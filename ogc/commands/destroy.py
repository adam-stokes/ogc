import sys

import click

from ogc.tasks import do_destroy

from ..provision import choose_provisioner
from ..state import app
from .base import cli


@click.command(help="Destroys a node and its associated keys, storage, etc.")
@click.option("--name", multiple=True, required=True)
def rm(name):
    _names = name
    app.log.info(f"Destroying: [{', '.join(_names)}]")
    for name in _names:
        do_destroy.delay(name, app.env)


@click.option("--provider", default="aws", help="Provider to query")
@click.option("--filter", required=False, help="Filter by keypair name")
@click.command(help="Remove keypairs")
def rm_key_pairs(provider, filter):
    engine = choose_provisioner(provider, env=app.env)
    kps = []
    if filter:
        kps = [kp for kp in engine.list_key_pairs() if filter in kp.name]
    else:
        kps = [kp for kp in engine.list_key_pairs()]

    for kp in kps:
        click.secho(f"Removing keypair: {kp.name}", fg="green")
        engine.delete_key_pair(kp)


cli.add_command(rm)
cli.add_command(rm_key_pairs)
