import sys

import click
import gevent
from gevent.pool import Pool

from ..cache import Cache
from ..provision import choose_provisioner
from ..state import app
from .base import cli


@click.command(help="Destroys a node and its associated keys, storage, etc.")
@click.option("--name", multiple=True, required=True)
def rm(name):
    _names = name
    for name in _names:
        cache_obj = Cache()
        node_data = None
        if not cache_obj.exists(name):
            app.log.error(f"Unable to find {layout.name} in cache")
            sys.exit(1)
        node_data = cache_obj.load(name)
        if node_data:
            uuid = node_data.id
            node = node_data.node
            layout = node_data.layout
            engine = choose_provisioner(layout.provider, env=app.env)
            node = engine.node(instance_id=node.id)
            app.log.info(f"Destroying {layout.name}")
            is_destroyed = node.destroy()
            if not is_destroyed:
                app.log.error(f"Unable to destroy {node.id}")

            key_pair = engine.get_key_pair(uuid)
            ssh_deleted_err = engine.delete_key_pair(key_pair)
            if ssh_deleted_err:
                app.log.error(f"Could not delete ssh keypair {uuid}")

            if not is_destroyed and ssh_deleted_err:
                sys.exit(1)
        cache_obj.delete(name)


@click.option("--provider", default="aws", help="Provider to query")
@click.option("--filter", required=False, help="Filter by keypair name")
@click.command(help="Remove keypairs")
def rm_key_pairs(provider, filter):
    engine = choose_provisioner(provider, env=app.env)
    kps = []
    if filter:
        kps = [kp for kp in engine.list_key_pairs() if filter in kp.name]
    else:
        kps = [kp for kp in engine.list_key_pairs()]

    pool = Pool(5)
    rm_jobs = []
    for kp in kps:
        click.secho(f"Removing keypair: {kp.name}", fg="green")
        rm_jobs.append(pool.spawn(engine.delete_key_pair, kp))

    gevent.joinall(rm_jobs)


cli.add_command(rm)
cli.add_command(rm_key_pairs)
