"""provisions machines"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, wait
from functools import partial
from multiprocessing import cpu_count

import click

from ogc import db
from ogc.commands.base import cli
from ogc.log import get_logger
from ogc.models import actions, layout, machine, tags
from ogc.provision import AWSProvisioner, GCEProvisioner

# Not advertised, but available for those who seek moar power.
MAX_WORKERS = int(os.environ.get("OGC_MAX_WORKERS", cpu_count() - 1))

dbi = db.connect()
dbi.create_tables(
    [machine.MachineModel, tags.TagModel, layout.LayoutModel, actions.ActionModel]
)


@click.command(help="Launch machines from layout configurations")
@click.argument("tag", type=str, metavar="tag")
def up(tag: str) -> None:
    """Launches machines from layout specifications by tag"""
    log = get_logger("ogc.commands.up")

    def _up_async(layout: layout.LayoutModel) -> None:
        _layout = db.pickle_to_model(layout)
        p = (
            GCEProvisioner(layout=_layout)
            if _layout.provider == "google"
            else AWSProvisioner(layout=_layout)
        )
        log.info("Provisioning")
        p.connect()
        log.info("Setup")
        p.setup()
        log.info("Creating")
        p.create()

    _layouts: list[layout.LayoutModel] = [
        _l for _l in layout.LayoutModel.select() if tag in _l.tags
    ]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(_up_async)
        results = [
            executor.submit(func, db.model_as_pickle(layout)) for layout in _layouts
        ]
        wait(results, timeout=5)


cli.add_command(up, name="up")
