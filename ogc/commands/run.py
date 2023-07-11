"""execute on machines"""
from __future__ import annotations

from pathlib import Path

import click

from ogc.commands.base import cli
from ogc.deployer import exec, exec_scripts
from ogc.models import layout


@click.command(help="Execute command against machines")
@click.argument("tag", type=str, metavar="tag", nargs=-1)
@click.argument("cmd", type=str, metavar="cmd")
def _exec(tag: str, cmd: str) -> None:
    """Launches machines from layout specifications by tag"""
    _layouts: list[layout.LayoutModel] = [
        _l for _l in layout.LayoutModel.query() if set(tag).intersection(_l.tags)
    ]
    opts = {"cmd": cmd}
    if tag:
        opts.update({"tag": tag})
    exec(_layouts, **opts)


@click.command(help="Execute scripts against machines")
@click.argument("tag", type=str, metavar="tag", nargs=-1)
@click.argument("script-dir", type=Path, metavar="path/to/script/or/dir")
def _exec_scripts(tag: str, script_dir: Path) -> None:
    """Launches machines from layout specifications by tag"""
    _layouts: list[layout.LayoutModel] = [
        _l for _l in layout.LayoutModel.query() if set(tag).intersection(_l.tags)
    ]
    opts = {"scripts": script_dir}
    if tag:
        opts.update({"tag": tag})
    exec_scripts(_layouts, **opts)


cli.add_command(_exec, name="exec")
cli.add_command(_exec_scripts, name="exec-scripts")
