import sys
from pathlib import Path
from statistics import multimode

import click
import gevent
from gevent.pool import Pool

from ..cache import Cache
from ..provision import ProvisionResult, choose_provisioner
from ..spec import SpecLoader
from ..state import app
from .base import cli


@click.command(help="Launches nodes from a provision specification")
@click.option("--spec", required=True, multiple=True)
def launch(spec):
    # Setup cache-dir
    cache_obj = Cache()

    specs = []
    # Check for local spec
    if Path("ogc.yml").exists() and not spec:
        specs.append(Path("ogc.yml"))

    for sp in spec:
        _path = Path(sp)
        if not _path.exists():
            app.log.error(f"Unable to find spec: {sp}")
            sys.exit(1)
        specs.append(_path)
    app.spec = SpecLoader.load(specs)

    pool = Pool(len(app.spec.layouts))
    create_jobs = []
    for layout in app.spec.layouts:
        engine = choose_provisioner(layout.provider, env=app.env)
        app.log.info(f"[{engine}] Launching: {layout.name}")
        engine.create_keypair(app.spec.ssh)
        create_jobs.append(
            pool.spawn(
                engine.create,
                layout,
                cache=cache_obj,
                ssh=app.spec.ssh,
                msg_cb=app.log.info,
            )
        )
    gevent.joinall(create_jobs)

    # Load up any stored metadata
    metadata = {}
    for layout in app.spec.layouts:
        if cache_obj.exists(layout.name):
            metadata[layout.name.replace("-", "_")] = cache_obj.load(layout.name)

    config_jobs = []
    for job in create_jobs:
        if job.value is not None:
            config_jobs.append(
                pool.spawn(
                    job.value["deployer"].run,
                    metadata=metadata,
                    ssh=app.spec.ssh,
                    msg_cb=app.log.info,
                )
            )

    gevent.joinall(config_jobs)

    for job in config_jobs:
        if job.value is not None and isinstance(job.value, ProvisionResult):
            job.value.render(msg_cb=app.log.info)


cli.add_command(launch)
