from __future__ import annotations

import sys
from pathlib import Path

import click
from dotenv import load_dotenv

import ogc.loader
import ogc.signals
from ogc import db
from ogc.log import get_logger
from ogc.models import actions, layout, machine, tags

dbi = db.connect()
dbi.create_tables(
    [machine.MachineModel, tags.TagModel, layout.LayoutModel, actions.ActionModel]
)


@click.command(help="Manage and Provision machines")
@click.option(
    "--options",
    "-o",
    multiple=True,
    help="Pass in -o KEY=VALUE -o KEY=VALUE which is used in the provision spec",
    metavar="KEY=VAL",
)
@click.option("--verbose", "-v", required=False, help="Turn on debug", is_flag=True)
@click.argument("spec", type=Path)
@click.argument("task", type=str)
def cli(options: list[str], verbose: bool, spec: Path, task: str) -> None:
    """Just a simple provisioner"""
    load_dotenv()
    log = get_logger("ogc", verbose)

    opts = {opt.split("=")[0]: opt.split("=")[1] for opt in options}

    mod = ogc.loader.from_path(spec)
    if not mod:
        log.error(f"Could not load {spec} into OGC.")
        sys.exit(1)
    ogc.loader.run(mod, task, **opts)


def start() -> None:
    """
    Starts app
    """
    cli()
