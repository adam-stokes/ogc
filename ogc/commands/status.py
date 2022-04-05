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
@click.option(
    "--output-file",
    required=False,
    help="Stores the table output to svg or html. Determined by the file extension.",
)
def status(reconcile, spec, output_file):
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

    console = Console(record=True)
    console.print(table, justify="center")
    if output_file:
        if output_file.endswith("svg"):
            console.save_svg(output_file, title="Node Status Output")
        elif output_file.endswith("html"):
            console.save_html(output_file)
        else:
            log.error(
                f"Unknown extension for {output_file}, must end in '.svg' or '.html'"
            )
            sys.exit(1)


cli.add_command(status)
