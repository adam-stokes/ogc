"""teardown machines"""
from __future__ import annotations

import os
from multiprocessing import cpu_count

import click
import structlog
from gevent.pool import Pool

from ogc import db
from ogc.commands.base import cli
from ogc.models import machine
from ogc.provision import BaseProvisioner

# Not advertised, but available for those who seek moar power.
MAX_WORKERS = int(os.environ.get("OGC_MAX_WORKERS", cpu_count() - 1))

log = structlog.getLogger()
pool = Pool(size=MAX_WORKERS)


@click.command(help="Destroy machines from layout configurations")
@click.option("--query", "-q", "query", help="Filter machines via attributes")
def down(query: str) -> None:
    """Destroys machines from layout specifications by tag"""
    cache = db.cache_path()

    def _down_async(machine: machine.MachineModel) -> None:
        provisioner = BaseProvisioner.from_machine(machine=machine)
        provisioner.destroy([machine.node])
        cache.delete(machine.node.id)
        log.info(f"{_machine.instance_name} destroyed")

    opts = {}
    if query:
        k, v = query.split("=")
        opts.update({k: v})

    _machines = db.query(**opts)
    if _machines:
        for _machine in _machines:
            log.info(f"Tearing down {_machine.node.name}")
            pool.spawn(_down_async, _machine)
        pool.join()


cli.add_command(down, name="down")
