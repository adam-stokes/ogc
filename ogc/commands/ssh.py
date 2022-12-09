# pylint: disable=unexpected-keyword-arg
from __future__ import annotations

import os
import sys
from pathlib import Path

import click
import sh
from dotenv import load_dotenv

import ogc.loader
from ogc import db
from ogc.log import CONSOLE, get_logger
from ogc.signals import after_provision

from .base import cli

log = get_logger("ogc")


@click.command(help="Login to a node")
@click.argument("instance")
def ssh(instance: str) -> None:
    load_dotenv()
    _db = db.Manager()
    instance_names = _db.nodes().keys()
    node = None
    if instance in instance_names:
        node = _db.nodes()[instance]

    if node:
        cmd = [
            "-i",
            str(node.ssh_private_key.expanduser()),
            f"{node.username}@{node.public_ip}",
        ]
        sh.ssh(cmd, _fg=True, _env=os.environ.copy())  # type: ignore
        sys.exit(0)


@click.command(help="Execute a command across node(s)")
@click.argument("spec", type=Path)
@click.argument("cmd", type=str)
def exec(spec: Path, cmd: str) -> None:
    deploy = ogc.loader.from_path(spec)
    if not deploy:
        log.error(f"Could not load {spec} into OGC.")
        sys.exit(1)
    with CONSOLE.status("Executing deployment command", spinner="aesthetic"):
        after_provision.send({"cmd": cmd})


@click.command(help="(R)Execute a set of scripts")
@click.argument("spec", type=Path)
@click.argument("path")
def exec_scripts(spec: Path, path: str) -> None:
    if not ogc.loader.from_path(spec):
        log.error(f"Could not load {spec} into OGC.")
        sys.exit(1)
    with CONSOLE.status("Executing deployment scripts", spinner="aesthetic"):
        after_provision.send({"path": path})


cli.add_command(ssh)
cli.add_command(exec)
cli.add_command(exec_scripts)
