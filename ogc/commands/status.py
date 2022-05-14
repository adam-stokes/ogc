import sys

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from ogc import actions
from ogc.log import Logger as log

from ..spec import SpecLoader, deploy_status, is_degraded
from ..spec import status as status_fn
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
def status(reconcile: bool, spec: list[str], output_file: str) -> None:
    _spec = SpecLoader.load(list(spec))

    counts = status_fn(_spec)

    if reconcile and is_degraded(_spec):
        log.info(f"Reconciling: {', '.join([layout.name for layout in _spec.layouts])}")
        actions.sync_async(layouts=_spec.layouts, overrides=counts)
        return

    table = Table(title=f"Deployment Status: {deploy_status(_spec)}")
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
