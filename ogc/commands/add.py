"""adds a application/injector/collector to environment"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import click
import structlog

from ogc import db
from ogc.commands.base import cli
from ogc.deployer import exec_scripts
from ogc.models import layout


@click.command(help="Add a service to machine")
@click.argument("service-dir", type=Path, metavar="path/to/service-dir")
@click.pass_obj
def _add(ctx_obj, service_dir: Path) -> None:
    """"""
    if not (service_dir / ".plan.yml").exists():
        log.error(
            "No .plan.yml found,  unable to process service",
            path=service_dir / ".plan.yml",
        )
        sys.exit(1)
    if not (service_dir / "install").exists():
        log.error(
            "No install hook found, unable to process service",
            path=service_dir / "install",
        )
        sys.exit(1)

    exec_scripts(service_dir / "install", **ctx_obj.opts)


cli.add_command(_add, name="add")
