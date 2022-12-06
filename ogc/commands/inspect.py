from __future__ import annotations

import sys

import arrow
import click
from rich.console import Console
from rich.padding import Padding

from ogc import db, models

from .base import cli


@click.command(help="List nodes in your inventory")
@click.option("--by-id", required=False, help="Inspect node by DB ID")
@click.option(
    "--by-name",
    required=False,
    help="Inspect nodes by name, this can be a substring match",
)
@click.option(
    "--by-tag",
    required=False,
    help="Inspect nodes by tag",
)
@click.option(
    "--action-id",
    required=False,
    help="If set will only show the action output for a specific action ID",
)
@click.option(
    "--extend/--no-extend",
    default=False,
    help="Show extended action output at once",
)
def inspect(
    by_id: str, by_name: str, by_tag: str, action_id: str, extend: bool
) -> None:
    _db = db.Manager()
    if by_tag and by_name and by_id:
        click.echo(
            click.style(
                "Combined filtered options are not supported, please choose one.",
                fg="red",
            )
        )
        sys.exit(1)

    rows: list[models.Machine] = list(_db.nodes().values())
    if by_tag:
        rows = [node for node in rows if by_tag in node.layout.tags]
    elif by_name:
        rows = [node for node in rows if node.instance_name == by_name]
    else:
        rows = [node for node in rows if node.id.split("-")[0] == by_id]

    console = Console()
    for data in rows:
        console.print(f"Deploy Details: [green]{data.instance_name}[/]")
        completed_actions = []
        failed_actions = []

        if not data.actions:
            console.print("[bold red]No actions found[/]")
            sys.exit(1)
        if action_id:
            actions = list(filter(lambda x: x.id == action_id, data.actions))
        else:
            actions = data.actions
        for action in actions:
            if action.exit_code != 0:
                failed_actions.append(action)
            else:
                completed_actions.append(action)

        if completed_actions:
            console.print(
                Padding(
                    f"[green]{len(completed_actions)}[/] successful actions:",
                    (1, 0, 1, 0),
                )
            )
            for action in completed_actions:
                console.print(
                    Padding(
                        f":: id: {action.id} :: timestamp: {arrow.get(action.created).humanize()}",
                        (0, 0, 0, 2),
                    )
                )
                if action_id or extend:
                    console.print(Padding(action.out + action.error, (0, 0, 0, 2)))

        if failed_actions:
            console.print(
                Padding(f"[red]{len(failed_actions)}[/] failed actions:", (1, 0, 1, 0))
            )
            for action in failed_actions:
                console.print(
                    Padding(
                        f":: id: {action.id} :: timestamp: {arrow.get(action.created).humanize()}",
                        (0, 0, 0, 2),
                    )
                )

                if action_id or extend:
                    if not action.out.strip() and action.error.strip():
                        console.print(Padding("No output", (0, 0, 0, 2)))
                    else:
                        console.print(Padding(action.out + action.error, (0, 0, 0, 2)))


cli.add_command(inspect)
