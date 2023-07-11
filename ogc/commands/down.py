"""teardown machines"""
from __future__ import annotations

import os
from multiprocessing import cpu_count

import click
from gevent.pool import Pool

from ogc import db
from ogc.commands.base import cli
from ogc.log import get_logger
from ogc.models import machine
from ogc.provision import BaseProvisioner

# Not advertised, but available for those who seek moar power.
MAX_WORKERS = int(os.environ.get("OGC_MAX_WORKERS", cpu_count() - 1))

log = get_logger("ogc.commands.down")
pool = Pool(size=MAX_WORKERS)


@click.command(help="Destroy machines from layout configurations")
@click.argument("tag", type=str, metavar="tag")
def down(tag: str) -> None:
    """Destroys machines from layout specifications by tag"""

    def _down_async(machine: machine.MachineModel) -> None:
        provisioner = BaseProvisioner.from_layout(layout=machine.layout)
        provisioner.destroy([machine.node])

    cache_nodes = db.cache_path()
    for _node in cache_nodes.iterkeys():
        _machine = db.pickle_to_model(cache_nodes.get(_node))
        log.info(f"Tearing down {_machine.node.name}")
        pool.spawn(_down_async, _machine)
    pool.join()
    cache_nodes.clear()


cli.add_command(down, name="down")
