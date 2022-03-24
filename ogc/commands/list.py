import sys

import click

from rich import print
from rich.console import Console
from rich.table import Table
from rich.text import Text
from ogc import db

from ..provision import choose_provisioner
from ..state import app
from .base import cli


@click.command(help="List nodes in your inventory")
@click.option("--by-tag", required=False, help="List nodes by tag")
@click.option(
    "--by-name",
    required=False,
    help="List nodes by name, this can be a substring match",
)
def ls(by_tag, by_name):
    if by_tag and by_name:
        click.echo(
            click.style(
                "Combined filtered options are not supported, please choose one.",
                fg="red",
            )
        )
        sys.exit(1)

    db.connect()
    rows = None
    if by_tag:
        rows = db.NodeModel.select().where(db.NodeModel.tags.contains(by_tag))
    elif by_name:
        rows = db.NodeModel.select().where(db.NodeModel.instance_name.contains(by_name))
    else:
        rows = db.NodeModel.select()
    table = Table()
    table.add_column(f"{len(rows)} Nodes")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Connection")
    table.add_column("Tags")
    table.add_column("Actions")

    for data in rows:
        completed_actions = []
        failed_actions = []
        for action in data.actions.select():
            if action.exit_code != 0:
                failed_actions.append(action)
            else:
                completed_actions.append(action)
        table.add_row(
                str(data.id),
                data.instance_name,
                data.instance_state,
                f"ssh -i {data.ssh_private_key} {data.username}@{data.public_ip}",
                ",\n".join(
                    [
                        f"[bold green]{tag}[/]"
                        if by_tag and tag == by_tag
                        else tag
                        for tag in data.tags
                    ]
                ),
                (
                    f"pass: [green]:heavy_check_mark:[/] "
                    f"fail: [red]{str(len(failed_actions)) if len(failed_actions) > 0 else len(failed_actions)}[/]"
                ),
        )

    console = Console()
    console.print(table)


@click.option("--provider", default="aws", help="Provider to query")
@click.option("--filter", required=False, help="Filter by keypair name")
@click.command(help="List keypairs")
def ls_key_pairs(provider, filter):
    engine = choose_provisioner(provider, env=app.env)
    kps = []
    if filter:
        kps = [kp for kp in engine.list_key_pairs() if filter in kp.name]
    else:
        kps = [kp for kp in engine.list_key_pairs()]

    for kp in kps:
        click.secho(kp.name, fg="green")


cli.add_command(ls)
cli.add_command(ls_key_pairs)
