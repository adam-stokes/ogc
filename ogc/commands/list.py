import click
from texttable import Texttable

from ..cache import Cache
from ..provision import choose_provisioner
from ..state import app
from .base import cli


@click.command(help="List nodes in your inventory")
def ls():
    cache_obj = Cache()
    inventory = cache_obj.inventory
    table = Texttable()
    table.set_cols_align(["l", "l", "l", "l"])
    table.set_cols_valign(["m", "m", "m", "m"])
    table.set_cols_width([20, 25, 10, 65])
    table.set_deco(Texttable.HEADER | Texttable.HLINES)
    table.add_row(["InstanceID", "Name", "Status", "Connection"])
    for node_name, data in inventory.items():
        layout = data["layout"]
        node_id = data["node"].id
        engine = choose_provisioner(layout.provider, env=app.env)
        node = engine.node(instance_id=node_id)
        table.add_row(
            [
                node.id,
                node_name,
                node.state,
                f"ssh -i {data['ssh_private_key']} {data['username']}@{data['host']}",
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
        click.secho(kp.name)

cli.add_command(ls)
cli.add_command(ls_key_pairs)
