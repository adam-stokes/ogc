from __future__ import annotations

import sys
from pathlib import Path

import click
from dotenv import load_dotenv

import ogc.loader
from ogc.log import CONSOLE, get_logger
from ogc.signals import ready_provision

from .base import cli

log = get_logger("ogc")


@click.command(help="Launches nodes from a provision specification")
@click.option(
    "--with-deploy/--with-no-deploy",
    default=True,
    help="Also performs script deployments",
)
@click.argument("spec", type=Path)
def launch(with_deploy: bool, spec: Path) -> None:
    load_dotenv()
    if not ogc.loader.from_path(spec):
        log.error(f"Could not load {spec} into OGC.")
        sys.exit(1)
    with CONSOLE.status("Provisioning machines", spinner="aesthetic"):
        ready_provision.send(dict(with_deploy=with_deploy))
    return


cli.add_command(launch)
