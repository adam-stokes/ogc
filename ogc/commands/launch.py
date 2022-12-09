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
    "--options",
    "-o",
    multiple=True,
    help="Pass in -o <key>=<value> -o <key>=<value> which is used in the provision spec",
)
@click.argument("spec", type=Path)
@click.argument("task", type=str, required=False)
def launch(options: list[str], spec: Path, task: str) -> None:
    load_dotenv()

    opts = {opt.split("=")[0]: opt.split("=")[1] for opt in options}

    mod = ogc.loader.from_path(spec)
    if not mod:
        log.error(f"Could not load {spec} into OGC.")
        sys.exit(1)
    if task:
        ogc.loader.run(mod, task, **opts)
    else:
        with CONSOLE.status("Provisioning machines", spinner="aesthetic"):
            ready_provision.send(opts)
    return


cli.add_command(launch)
