import sys
from pathlib import Path
from statistics import multimode

import click
import gevent
from gevent.pool import Pool

from ..cache import Cache
from ..provision import Deployer, DeployerResult, ProvisionResult, choose_provisioner
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
    pool = Pool(len(app.spec.layouts) + 2)
    create_jobs = []
    app.log.info(
        f"Launching: [{', '.join([layout.name for layout in app.spec.layouts])}]"
    )
    for layout in app.spec.layouts:
        engine = choose_provisioner(layout.provider, env=app.env)
        engine.setup(layout)
        create_jobs.append(
            pool.spawn(
                engine.create,
                layout=layout,
                env=app.env,
            )
        )
    gevent.joinall(create_jobs)

    # Load up any stored metadata
    metadata = {}
    for layout in app.spec.layouts:
        if cache_obj.exists(layout.name):
            metadata[layout.name.replace("-", "_")] = cache_obj.load(layout.name)

    config_jobs = []
    app.log.info(
        f"Executing Deployment(s) on: [{', '.join([layout.name for layout in app.spec.layouts])}]"
    )
    for job in create_jobs:
        if job.value is not None and isinstance(job.value, ProvisionResult):
            config_jobs.append(
                pool.spawn(
                    Deployer(job.value).run,
                    context=metadata,
                    msg_cb=app.log.info,
                )
            )

    gevent.joinall(config_jobs)

    for job in config_jobs:
        if job.value is not None and isinstance(job.value, DeployerResult):
            job.value.show(msg_cb=app.log.info)


cli.add_command(launch)
