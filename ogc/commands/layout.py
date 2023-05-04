"""Manages layouts"""
from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml

from ogc import db
from ogc.commands.base import cli
from ogc.log import get_logger
from ogc.models import actions, layout, machine, tags

dbi = db.connect()
dbi.create_tables(
    [machine.MachineModel, tags.TagModel, layout.LayoutModel, actions.ActionModel]
)


@click.group()
def _layout() -> None:
    """Layout manager"""


@click.command(help="Import layouts from specification")
@click.argument("spec", type=Path, metavar="<layouts.yml>")
def _import(spec: Path) -> None:
    """Manages layouts"""
    log = get_logger("ogc.commands.layout.import")
    if not spec.exists():
        log.critical(f"Unable to locate {spec}, please double check the path.")
        sys.exit(1)

    layouts_from_spec = yaml.safe_load(spec.read_text())
    for item in layouts_from_spec["layouts"]:
        layout.LayoutModel.get_or_create(**item)

    for item in layout.LayoutModel.select():
        log.info(f"Added layout: {item.id}:{item.runs_on} - {item.tags}")


_layout.add_command(_import, name="import")
cli.add_command(_layout, name="layout")
