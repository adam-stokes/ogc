import click
from texttable import Texttable

from ogc import db

from ..provision import choose_provisioner
from ..state import app
from .base import cli


@click.command(help="List nodes in your inventory")
def ls():
    db.connect()
    rows = db.NodeModel.select()
    table = Texttable()
    table.set_cols_width([10, 40, 10, 65])
    table.set_deco(Texttable.HEADER | Texttable.HLINES)
    table.add_row([f"{len(rows)} Nodes", "Name", "Status", "Connection"])

    for data in rows:
        table.add_row(
            [
                data.id,
                data.instance_name,
                data.instance_state,
                f"ssh -i {data.ssh_private_key} {data.username}@{data.public_ip}",
            ]
        )

    click.secho(table.draw())


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
