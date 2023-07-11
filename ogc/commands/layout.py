"""Manages layouts"""
from __future__ import annotations

import io
import shutil
import sys
from pathlib import Path

import click
import yaml

from ogc import db
from ogc.commands.base import cli
from ogc.deployer import ls_layouts
from ogc.log import get_logger
from ogc.models import layout
from ogc.provision import BaseProvisioner


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

    log.info(f"Adding {len(layouts_from_spec['layouts'])} layout(s) to cache.")
    layout.LayoutModel.create_from_specs(specs=layouts_from_spec["layouts"])


@click.command(help="List imported layouts")
@click.option("--as-yaml", is_flag=True, help="Output as YAML")
@click.option("--as-json", is_flag=True, help="Output as JSON")
@click.argument("tag", type=str, metavar="tag", nargs=-1)
def _list(as_yaml: bool, as_json: bool, tag: str) -> None:
    """Lists layouts"""
    log = get_logger("ogc.commands.layout.list")
    _layout: list[layout.LayoutModel] = layout.LayoutModel.query()
    if not _layout:
        log.info("No layouts defined.")
        return
    provisioner = BaseProvisioner.from_layout(layout=_layout[0], connect=False)
    opts = {}
    if tag:
        opts.update({"tag": tag})
    if as_yaml:
        opts.update({"yaml": as_yaml})
    if as_json:
        opts.update({"json": as_json})
    ls_layouts(provisioner=provisioner, **opts)


@click.command(help="Remove imported layouts")
@click.option("--all", is_flag=True, help="Remove all layouts")
@click.argument("name", type=str, metavar="name", nargs=-1)
def _rm(all: bool, name: str) -> None:
    """Remove layouts layouts"""
    log = get_logger("ogc.commands.layout.rm")
    cache = db.cache_layout_path()
    if all:
        log.info("Removing all layouts")
        cache.clear()

    if name:
        log.info(f"Removing {name[0]} layout")
        model = layout.LayoutModel.query(name=name)[0]
        cache.delete(model.id)
        if not model:
            log.warning(f"Layout {name} doesn't exist.")
            return


_layout.add_command(_import, name="import")
_layout.add_command(_list, name="ls")
_layout.add_command(_rm, name="rm")
cli.add_command(_layout, name="layout")
