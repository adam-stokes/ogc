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
@click.option(
    "--action-id",
    required=False,
    help="If set will only show the action output for a specific action ID",
)
def inspect(id, name, tag, action_id):
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
        if action_id:
            actions = data.actions.select().where(db.NodeActionResult.id == action_id)
        else:
            actions = data.actions.select()
        for action in actions:
            if action.exit_code != 0:
                failed_actions.append(action)
            else:
                completed_actions.append(action)

        if completed_actions:
            click.echo(f"[{len(completed_actions)}] Successful Actions:")
            click.echo()
            for action in completed_actions:
                if action.out.strip():
                    click.echo(f"(id: {action.id}) Out: {action.created}")
                    click.echo(click.style(action.out, fg="green"))
                if action.error:
                    click.echo(f"(id: {action.id}) Error:")
                    click.echo(click.style(action.error, fg="green"))

        if failed_actions:
            click.echo(f"[{len(failed_actions)}] Failed Actions:")
            click.echo()
            for action in failed_actions:
                if action.out.strip():
                    click.echo(f"(id: {action.id}) Out: {action.created}")
                    click.echo(click.style(action.out, fg="red"))
                if action.error:
                    click.echo(f"(id: {action.id}) Error:")
                    click.echo(click.style(action.error, fg="red"))


cli.add_command(inspect)
