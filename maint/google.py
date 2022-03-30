#!/usr/bin/env python
"""
Maintenance script for Google. Helps clean up instances and firewalls.
"""

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


cli.add_command(ls_firewalls)

if __name__ == "__main__":
    cli()