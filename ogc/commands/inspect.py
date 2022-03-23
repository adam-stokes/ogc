import sys

import click

from ogc import db

from .base import cli


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
def inspect(id, name, tag):
    if tag and name and id:
        click.echo(
            click.style(
                "Combined filtered options are not supported, please choose one.",
                fg="red",
            )
        )
        sys.exit(1)

    db.connect()
    rows = None
    if tag:
        rows = db.NodeModel.select().where(db.NodeModel.tags.contains(tag))
    elif name:
        rows = db.NodeModel.select().where(db.NodeModel.instance_name == name)
    else:
        rows = db.NodeModel.select().where(db.NodeModel.id == id)

    for data in rows:
        click.echo(f"Deploy Details: [{data.instance_name}]")
        completed_actions = []
        failed_actions = []
        for action in data.actions.select():
            if action.exit_code != 0:
                failed_actions.append(action)
            else:
                completed_actions.append(action)

        if completed_actions:
            click.echo(f"[{len(completed_actions)}] Successful Actions:")
            for action in completed_actions:
                if action.out.strip():
                    click.echo("Out:")
                    click.echo(click.style(action.out, fg="green"))
                if action.error:
                    click.echo("Error:")
                    click.echo(click.style(action.error, fg="green"))

        if failed_actions:
            click.echo(f"[{len(failed_actions)}] Failed Actions:")
            for action in failed_actions:
                if action.out.strip():
                    click.echo("Out:")
                    click.echo(click.style(action.out, fg="red"))
                if action.error:
                    click.echo("Error:")
                    click.echo(click.style(action.error, fg="red"))


cli.add_command(inspect)
