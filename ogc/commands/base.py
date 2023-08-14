from __future__ import annotations

import logging
import os
from multiprocessing import cpu_count

import click
from dotenv import load_dotenv

# Not advertised, but available for those who seek moar power.
MAX_WORKERS = int(os.environ.get("OGC_MAX_WORKERS", cpu_count() - 1))


@click.option("--verbose", "-v", is_flag=True, help="Increase logging verbosity")
@click.group()
def cli(verbose: bool) -> None:
    """Just a simple provisioner"""
    load_dotenv()
    logging.getLogger("ogc")


def start() -> None:
    """
    Starts app
    """
    cli()
