#!/usr/bin/env python
"""
Maintenance script for Google. Helps clean up instances and firewalls.
"""

import os
import click
from click_didyoumean import DYMGroup
from ogc.provision import choose_provisioner
from ogc.state import app

@click.group(cls=DYMGroup)
def cli():
    pass

@click.command()
@click.option("--contains", required=True, default="ogc", help="Firewall name contains string")
@click.option(
    "--with-delete/--no-with-delete",
    default=False,
    help="Delete found firewalls",
)
def ls_firewalls(contains, with_delete):
    """List GCP Firewalls"""
    engine = choose_provisioner("google", app.env)
    for fw in engine.list_firewalls():
        if fw.name.startswith(contains):
            if with_delete:
                click.secho(f"Deleting {fw.name}")
                engine.delete_firewall(fw.name)
            else:
                click.secho(f"Firewall found: {fw.name}")

@click.command()
@click.option("--by-tag", required=True, default=f"user-{os.environ.get('USER', '')}", help="Tag of user")
@click.option(
    "--with-delete/--no-with-delete",
    default=False,
    help="Delete found instances",
)
def ls_vms(by_tag, with_delete):
    """List GCP Firewalls"""
    engine = choose_provisioner("google", app.env)
    from pprint import pprint
    for node in engine.provisioner.list_nodes():
        if by_tag in node.extra['tags']:
            click.secho(f"{'Deleting' if with_delete else ''} ({node.id}) - {node.name}")
            if with_delete:
                node.destroy()

cli.add_command(ls_firewalls)
cli.add_command(ls_vms)

if __name__ == "__main__":
    cli()