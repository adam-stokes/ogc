import sys

import click
from prettytable import DOUBLE_BORDER, PrettyTable

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
    table = PrettyTable()
    table.field_names = [f"{len(rows)} Nodes", "Name", "Status", "Connection", "Tags"]

    for data in rows:
        table.add_row(
            [
                data.id,
                data.instance_name,
                data.instance_state,
                f"ssh -i {data.ssh_private_key} {data.username}@{data.public_ip}",
                ",\n".join(
                    [
                        click.style(tag, fg="green")
                        if by_tag and tag == by_tag
                        else tag
                        for tag in data.tags
                    ]
                ),
            ]
        )

    table.align = "l"
    table.set_style(DOUBLE_BORDER)
    click.echo(table)


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
