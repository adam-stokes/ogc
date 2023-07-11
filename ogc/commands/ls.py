"""ls machines"""
from __future__ import annotations

import click

from ogc.commands.base import cli
from ogc.deployer import ls
from ogc.models import layout
from ogc.provision import BaseProvisioner


@click.command(help="Launch machines from layout configurations")
@click.option("--as-yaml", is_flag=True, help="Output as YAML")
@click.option("--as-json", is_flag=True, help="Output as JSON")
@click.argument("tag", type=str, metavar="tag", nargs=-1)
def _ls(as_yaml: bool, as_json: bool, tag: str) -> None:
    """Lists machines"""
    _layout: list[layout.LayoutModel] = layout.LayoutModel.query()
    if _layout:
        _obj = _layout.pop()
        provisioner = BaseProvisioner.from_layout(layout=_obj, connect=False)
        opts = {}
        if tag:
            opts.update({"tag": tag})
        if as_yaml:
            opts.update({"yaml": as_yaml})
        if as_json:
            opts.update({"json": as_json})
        ls(provisioner=provisioner, **opts)


cli.add_command(_ls, name="ls")
