"""provisions machines"""
from __future__ import annotations

import click

from ogc import db
from ogc.commands.base import cli
from ogc.deployer import up as d_up
from ogc.models import layout

dbi = db.connect()


@click.command(help="Launch machines from layout configurations")
@click.argument("tag", type=str, metavar="tag", nargs=-1)
def up(tag: str) -> None:
    """Launches machines from layout specifications by tag"""
    _layouts: list[layout.LayoutModel] = [
        _l for _l in layout.LayoutModel.select() if set(tag).intersection(_l.tags)
    ]
    d_up(_layouts)


cli.add_command(up, name="up")
