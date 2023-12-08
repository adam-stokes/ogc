from __future__ import annotations

import logging
import os
from multiprocessing import cpu_count

import click
import structlog
from dotenv import load_dotenv

# Not advertised, but available for those who seek moar power.
MAX_WORKERS = int(os.environ.get("OGC_MAX_WORKERS", cpu_count() - 1))

logging.getLogger("paramiko").setLevel(logging.WARNING)


class CliCtx:
    def __init__(self, query=None):
        self.query = query
        self.opts = {}
        if self.query:
            k, v = self.query.split("=")
            self.opts.update({k: v})


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Increase logging verbosity")
@click.option("--query", "-q", "query", help="Filter machines via attributes")
@click.pass_context
def cli(ctx, verbose: bool, query: str) -> None:
    """Just a simple provisioner"""
    level = logging.DEBUG if verbose else os.environ.get("OGC_LOG_LEVEL", logging.INFO)
    load_dotenv()
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(level),
    )
    ctx.obj = CliCtx(query=query)


def start() -> None:
    """
    Starts app
    """
    cli()
