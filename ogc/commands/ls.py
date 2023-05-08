"""ls machines"""
from __future__ import annotations

import click

from ogc import db
from ogc.commands.base import cli
from ogc.deployer import ls
from ogc.models import layout
from ogc.provision import BaseProvisioner

dbi = db.connect()


@click.command(help="Launch machines from layout configurations")
@click.option("--as-yaml", is_flag=True, help="Output as YAML")
@click.option("--as-json", is_flag=True, help="Output as JSON")
@click.argument("tag", type=str, metavar="tag", nargs=-1)
def _ls(as_yaml: bool, as_json: bool, tag: str) -> None:
    """Launches machines from layout specifications by tag"""
    _layout: layout.LayoutModel = layout.LayoutModel.select().first()
    provisioner = BaseProvisioner.from_layout(layout=_layout, connect=False)
    opts = {}
    if tag:
        opts.update({"tag": tag})
    if as_yaml:
        opts.update({"yaml": as_yaml})
    if as_json:
        opts.update({"json": as_json})
    ls(provisioner=provisioner, **opts)


cli.add_command(_ls, name="ls")
