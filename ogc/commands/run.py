"""execute on machines"""
from __future__ import annotations

from pathlib import Path

import click

from ogc import db
from ogc.commands.base import cli
from ogc.deployer import exec, exec_scripts


@click.command(help="Execute command against machines")
@click.option("--query", "-q", "query", help="Filter machines via attributes")
@click.argument("cmd", type=str, metavar="cmd")
def _exec(query: str, cmd: str) -> None:
    """Executes commands on machines by tag"""
    opts = {}
    if query:
        k, v = query.split("=")
        opts.update({k: v})

    _machines = db.query(**opts)
    if _machines:
        exec(_machines, cmd)


@click.command(help="Execute scripts against machines")
@click.option("--query", "-q", "query", help="Filter machines via attributes")
@click.argument("script-dir", type=Path, metavar="path/to/script/or/dir")
def _exec_scripts(query: str, script_dir: Path) -> None:
    """Launches machines from layout specifications by tag"""
    opts = {}
    if query:
        k, v = query.split("=")
        opts.update({k: v})

    _machines = db.query(**opts)
    if _machines:
        exec_scripts(_machines, script_dir)


cli.add_command(_exec, name="exec")
cli.add_command(_exec_scripts, name="exec-scripts")
