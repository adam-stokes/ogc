"""execute on machines"""
from __future__ import annotations

from pathlib import Path

import click

from ogc import db
from ogc.commands.base import cli
from ogc.deployer import exec, exec_scripts, ssh
from ogc.provision import BaseProvisioner


@click.command(help="Execute command against machines")
@click.argument("cmd", type=str, metavar="cmd")
@click.pass_obj
def _exec(ctx_obj, cmd: str) -> None:
    """Executes commands on machines by tag"""
    exec(cmd, **ctx_obj.opts)


@click.command(help="Execute scripts against machines")
@click.argument("script-dir", type=Path, metavar="path/to/script/or/dir")
@click.pass_obj
def _exec_scripts(ctx_obj, script_dir: Path) -> None:
    """Launches machines from layout specifications by tag"""
    exec_scripts(script_dir, **ctx_obj.opts)


@click.command(help="SSH into machine")
@click.pass_obj
def _ssh(ctx_obj) -> None:
    """ssh into machine"""
    _machines = db.query(**ctx_obj.opts)
    ssh(provisioner=BaseProvisioner.from_machine(machine=_machines[0]))


cli.add_command(_exec, name="exec")
cli.add_command(_exec_scripts, name="exec-scripts")
cli.add_command(_ssh, name="ssh")
