from __future__ import annotations

import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.status import Status

import ogc.loader
from ogc.db import ui_nodes_table
from ogc.enums import RESERVED_TASKS
from ogc.log import CONSOLE, get_logger
from ogc.ssh import ssh


@click.command(help="Manage and Provision machines")
@click.option(
    "--options",
    "-o",
    multiple=True,
    help="Pass in -o KEY=VALUE -o KEY=VALUE which is used in the provision spec",
    metavar="KEY=VAL",
)
@click.option("--verbose", "-v", required=False, help="Turn on debug", is_flag=True)
@click.argument("task", type=str)
@click.argument("spec", type=Path)
def cli(options: list[str], verbose: bool, task: str, spec: Path) -> None:
    """Just a simple provisioner"""
    load_dotenv()
    log = get_logger("ogc", verbose)

    opts = {opt.split("=")[0]: opt.split("=")[1] for opt in options}
    opts["status"] = Status("Running", console=CONSOLE)

    if task in RESERVED_TASKS:
        match task.lower():
            case "ls":
                return ui_nodes_table(output_file=opts.get("output_file", None))
            case "ssh":
                # Special case, treat spec as a instance target
                return ssh(str(spec))

    mod = ogc.loader.from_path(spec)
    if not mod:
        log.error(f"Could not load {spec} into OGC.")
        sys.exit(1)
    if task:
        ogc.loader.run(mod, task, **opts)


def start() -> None:
    """
    Starts app
    """
    cli()
