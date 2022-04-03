import sys

import arrow
import click
from rich.console import Console
from rich.padding import Padding

from ogc import db, state

from .base import cli

if not state.app.engine:
    state.app.engine = db.connect()
    state.app.session = db.session(state.app.engine)


@click.command(help="List nodes in your inventory")
@click.option("--id", required=False, help="Inspect node by DB ID")
@click.option(
    "--name",
    required=False,
    help="Inspect nodes by name, this can be a substring match",
)
@click.option(
    "--tag",
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
def inspect(id, name, tag, action_id, extend):
    if tag and name and id:
        click.echo(
            click.style(
                "Combined filtered options are not supported, please choose one.",
                fg="red",
            )
        )
        sys.exit(1)

    rows = []
    with state.app.session as session:
        if tag:
            rows = session.query(db.Node).filter(db.Node.tags.contains([tag]))
        elif name:
            rows = session.query(db.Node).filter(db.Node.instance_name == name)
        else:
            rows = session.query(db.Node).filter(db.Node.id == id)

    console = Console()
    for data in rows:
        console.print(f"Deploy Details: [green]{data.instance_name}[/]")
        completed_actions = []
        failed_actions = []
        if action_id:
            actions = data.actions.filter(db.Actions.id == action_id)
        else:
            actions = data.actions.all()
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
                if action.out.strip():
                    console.print(
                        Padding(
                            f":: id: {action.id} :: timestamp: {arrow.get(action.created).humanize()}",
                            (0, 0, 0, 2),
                        )
                    )
                    if action_id or extend:
                        console.print(Padding(action.out, (0, 0, 0, 2)))
                if action.error:
                    console.print(
                        Padding(
                            f":: id: {action.id} :: timestamp: {arrow.get(action.created).humanize()}",
                            (0, 0, 0, 2),
                        )
                    )
                    if action_id or extend:
                        console.print(Padding(action.error, (0, 0, 0, 2)))

        if failed_actions:
            console.print(
                Padding(f"[red]{len(failed_actions)}[/] failed actions:", (1, 0, 1, 0))
            )
            for action in failed_actions:
                if action.out.strip():
                    console.print(
                        Padding(
                            f":: id: {action.id} :: timestamp: {arrow.get(action.created).humanize()}",
                            (0, 0, 0, 2),
                        )
                    )
                    if action_id or extend:
                        console.print(Padding(action.out, (0, 0, 0, 2)))
                if action.error:
                    console.print(
                        Padding(
                            f":: id: {action.id} :: timestamp: {arrow.get(action.created).humanize()}",
                            (0, 0, 0, 2),
                        )
                    )
                    if action_id or extend:
                        console.print(Padding(action.error, (0, 0, 0, 2)))


cli.add_command(inspect)
