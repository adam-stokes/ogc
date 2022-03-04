import sys

import click

from ..cache import Cache
from ..provision import choose_provisioner
from ..state import app
from .base import cli


@click.command(help="Destroys a node and it's associated keys, storage, etc.")
@click.argument("name")
def destroy(name):
    cache_obj = Cache()
    node_data = None
    if cache_obj.exists(name):
        node_data = cache_obj.load(name)
    if node_data:
        uuid = node_data["uuid"]
        node = node_data["node"]
        layout = node_data["layout"]
        engine = choose_provisioner(layout.provider, env=app.env)
        node = engine.node(instance_id=node.id)
        app.log.info(f"Destroying {layout.name}")
        is_destroyed = node.destroy()
        if not is_destroyed:
            app.log.error(f"Unable to destroy {node.id}")

        is_ssh_deleted = engine.delete_key_pair(uuid)
        if not is_ssh_deleted:
            app.log.error(f"Could not delete ssh keypair {engine.uuid}")

        if not is_destroyed and not is_ssh_deleted:
            sys.exit(1)


cli.add_command(destroy)
