import sys

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text
from toolz import thread_last
from toolz.curried import filter

from ogc import actions
from ogc.db import M, get_user
from ogc.deployer import convert_msd_to_actions
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
    user = get_user().unwrap()
    user.spec = SpecLoader.load(list(spec))

    counts = status_fn(user.spec)

    if reconcile and is_degraded(user.spec):
        log.info(
            f"Reconciling: {', '.join([layout.name for layout in user.spec.layouts])}"
        )
        nodes = actions.sync_async(
            layouts=user.spec.layouts, user=user, overrides=counts
        )
        added_nodes = [
            node for node in nodes if counts[node.layout.name]["action"] == "add"
        ]
        deleted_nodes = [
            node for node in nodes if counts[node.layout.name]["action"] == "remove"
        ]
        if added_nodes:
            actions.deploy_async(nodes=added_nodes)

        if deleted_nodes:
            thread_last(
                nodes,
                filter(lambda x: counts[x.layout.name]["action"] == "remove"),
                lambda x: x.instance_name,
                M.delete,
            )
        return

    table = Table(title=f"Deployment Status: {deploy_status(user.spec)}")
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
