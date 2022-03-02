import sys
from collections import deque
from pathlib import Path

import click
import gevent
from gevent.pool import Pool

from ..provision import ProvisionResult, choose_provisioner
from ..spec import SpecLoader
from ..state import app


@click.option(
    "--spec", metavar="<spec>", required=False, multiple=True, help="OGC Spec"
)
@click.command()
def cli(spec):
    """Processes a OGC Spec"""
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

    app.log.debug(app.env)

    if not app.spec.providers:
        app.log.error("No providers defined, please define at least 1 to proceed.")
        sys.exit(1)

    pool = Pool(len(app.spec.layouts))
    create_jobs = []
    for provider, options in app.spec.providers.items():
        engine = choose_provisioner(provider, options, app.env)
        app.log.info(f"Creating ssh credentials from {app.spec.ssh.public}")
        engine.create_ssh_keypair(app.spec.ssh)
        app.log.info(f"Using provisioner: {engine}")
        for layout in app.spec.layouts:
            if layout.provider and provider == layout.provider:
                create_jobs.append(
                    pool.spawn(
                        engine.create, layout, ssh=app.spec.ssh, msg_cb=app.log.info
                    )
                )
    gevent.joinall(create_jobs)

    config_jobs = []
    for job in create_jobs:
        if job.value is not None:
            config_jobs.append(
                pool.spawn(
                    job.value["deployer"].run, ssh=app.spec.ssh, msg_cb=app.log.info
                )
            )

    gevent.joinall(config_jobs)

    for job in config_jobs:
        if job.value is not None and isinstance(job.value, ProvisionResult):
            job.value.render(msg_cb=app.log.info)


def start():
    """
    Starts app
    """
    cli()
