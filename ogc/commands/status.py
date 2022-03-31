import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from ogc import actions
from ogc.log import Logger as log

from ..spec import SpecLoader
from ..state import app
from .base import cli


@click.command(help="Get status of deployment")
@click.option(
    "--reconcile/--no-reconcile",
    default=False,
    help="Attempt to fix deployment to match scale",
)
@click.option("--spec", required=False, multiple=True)
def status(reconcile, spec):
    app.spec = SpecLoader.load(list(spec))
    counts = app.spec.status

    if reconcile and app.spec.is_degraded:
        log.info(
            f"Reconciling: {', '.join([layout.name for layout in app.spec.layouts])}"
        )
        actions.sync_async(app.spec.layouts, counts)
        return

    table = Table(title=f"Deployment Status: {app.spec.deploy_status}")
    table.add_column("Name")
    table.add_column("Deployed")
    table.add_column("Scale")
    table.add_column("Remaining")
    for name, stats in counts.items():
        if stats["remaining"] > 0 or stats["remaining"] < 0:
            table.add_row(
                name,
                str(stats["deployed"]),
                str(stats["scale"]),
                Text(str(stats["remaining"]), style="bold red"),
            )
        else:
            table.add_row(
                name,
                str(stats["deployed"]),
                str(stats["scale"]),
                Text(str(stats["remaining"]), style="bold green"),
            )

    console = Console()
    console.print(table)


cli.add_command(status)
