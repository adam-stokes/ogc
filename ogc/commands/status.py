import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from ogc import log
from ogc.actions import sync

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
    # Db connection
    specs = []
    # Check for local spec
    if Path("ogc.yml").exists() and not spec:
        specs.append(Path("ogc.yml"))

    for sp in spec:
        _path = Path(sp)
        if not _path.exists():
            log.error(f"Unable to find spec: {sp}")
            sys.exit(1)
        specs.append(_path)

    if not specs:
        log.error("No provision specs found, please specify with `--spec <file.yml>`")
        sys.exit(1)

    app.spec = SpecLoader.load(specs)
    counts = app.spec.status

    if reconcile and app.spec.is_degraded:
        log.info(
            f"Reconciling: [{', '.join([layout.name for layout in app.spec.layouts])}]"
        )
        sync(app.spec.layouts, counts, app.env)
        return

    deploy_status = (
        "[bold green]Healthy[/]"
        if not app.spec.is_degraded
        else "[bold red]Degraded[/]"
    )

    table = Table(title=f"Deployment Status: {deploy_status}")
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
