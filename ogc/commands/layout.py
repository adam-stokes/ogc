"""Manages layouts"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import click
import yaml

from ogc import db
from ogc.commands.base import cli
from ogc.deployer import ls_layouts
from ogc.log import get_logger
from ogc.models import actions, layout, machine, tags
from ogc.provision import BaseProvisioner

dbi = db.connect()
dbi.create_tables(
    [machine.MachineModel, tags.TagModel, layout.LayoutModel, actions.ActionModel]
)


@click.group()
def _layout() -> None:
    """Layout manager"""


@click.command(help="Import layouts from specification")
@click.argument(
    "spec", type=click.File("r"), default=sys.stdin, metavar="<layouts.yml>"
)
def _import(spec: Path) -> None:
    """Manages layouts"""
    log = get_logger("ogc.commands.layout.import")

    if not isinstance(spec, io.TextIOWrapper) and not spec.exists():
        log.critical(f"Unable to locate {spec}, please double check the path.")
        sys.exit(1)

    layouts_from_spec = None
    if isinstance(spec, io.TextIOWrapper):
        layouts_from_spec = yaml.safe_load(spec.read())
    else:
        layouts_from_spec = yaml.safe_load(spec.read_text())

    for item in layouts_from_spec["layouts"]:
        layout.LayoutModel.get_or_create(**item)

    for item in layout.LayoutModel.select():
        log.info(f"Added layout: {item.id}:{item.runs_on} - {item.tags}")


@click.command(help="List imported layouts")
@click.option("--as-yaml", is_flag=True, help="Output as YAML")
@click.option("--as-json", is_flag=True, help="Output as JSON")
@click.argument("tag", type=str, metavar="tag", nargs=-1)
def _list(as_yaml: bool, as_json: bool, tag: str) -> None:
    """Lists layouts"""
    log = get_logger("ogc.commands.layout.list")
    _layout: layout.LayoutModel = layout.LayoutModel.select().first()
    provisioner = BaseProvisioner.from_layout(layout=_layout, connect=False)
    opts = {}
    if tag:
        opts.update({"tag": tag})
    if as_yaml:
        opts.update({"yaml": as_yaml})
    if as_json:
        opts.update({"json": as_json})
    ls_layouts(provisioner=provisioner, **opts)


_layout.add_command(_import, name="import")
_layout.add_command(_list, name="ls")
cli.add_command(_layout, name="layout")
