"""teardown machines"""
from __future__ import annotations

import os
from multiprocessing import cpu_count

import click
from gevent.pool import Pool

from ogc import db
from ogc.commands.base import cli
from ogc.log import get_logger
from ogc.models import layout
from ogc.provision import BaseProvisioner

# Not advertised, but available for those who seek moar power.
MAX_WORKERS = int(os.environ.get("OGC_MAX_WORKERS", cpu_count() - 1))

dbi = db.connect()
pool = Pool(size=MAX_WORKERS)


@click.command(help="Destroy machines from layout configurations")
@click.argument("tag", type=str, metavar="tag")
def down(tag: str) -> None:
    """Destroys machines from layout specifications by tag"""

    def _down_async(layout: layout.LayoutModel) -> None:
        provisioner = BaseProvisioner.from_layout(layout=layout)
        provisioner.destroy(nodes=layout.machines)
        for machine in layout.machines:
            machine.delete_instance()

    _layouts: list[layout.LayoutModel] = [
        _l for _l in layout.LayoutModel.select() if tag in _l.tags
    ]
    for _layout in _layouts:
        pool.spawn(_down_async, _layout)
    pool.join()


cli.add_command(down, name="down")
