import sys
from pathlib import Path

import click
from prettytable import DOUBLE_BORDER, PrettyTable

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
@click.option("--spec", required=True, multiple=True)
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
    app.spec = SpecLoader.load(specs)
    counts = app.spec.status

    if reconcile and app.spec.is_degraded:
        log.info(
            f"Reconciling: [{', '.join([layout.name for layout in app.spec.layouts])}]"
        )
        sync(app.spec.layouts, counts, app.env)
        return

    table = PrettyTable()
    table.field_names = ["Name", "Deployed", "Scale", "Remaining"]
    for name, stats in counts.items():
        if stats["remaining"] > 0 or stats["remaining"] < 0:
            table.add_row(
                [
                    name,
                    stats["deployed"],
                    stats["scale"],
                    click.style(stats["remaining"], fg="red"),
                ]
            )
        else:
            table.add_row(
                [
                    name,
                    stats["deployed"],
                    stats["scale"],
                    click.style(stats["remaining"], fg="green"),
                ]
            )

    table.align = "l"
    table.set_style(DOUBLE_BORDER)
    click.echo(table)
    click.echo()
    deploy_status = (
        click.style("Healthy", fg="green")
        if not app.spec.is_degraded
        else click.style("Degraded", fg="red")
    )
    click.echo(f"Deployment Status: {deploy_status}")


cli.add_command(status)
