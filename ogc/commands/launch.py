import sys
from pathlib import Path

import click
from celery import chord

from ogc.tasks import do_deploy, do_provision, end_deploy, end_provision

from ..provision import DeployerResult, ProvisionResult
from ..spec import SpecLoader
from ..state import app
from .base import cli


@click.command(help="Launches nodes from a provision specification")
@click.option("--spec", required=True, multiple=True)
def launch(spec):
    # Setup cache-dir
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
    app.log.info(
        f"Provisioning: [{', '.join([layout.name for layout in app.spec.layouts])}]"
    )

    create_jobs = [do_provision.s(layout, app.env) for layout in app.spec.layouts]

    callback = end_provision.s()
    result = chord(create_jobs)(callback)
    results = result.get()

    # Load up any stored metadata
    # TODO: move this to a database for better async
    metadata = {}
    for job in results:
        metadata[job.layout.name.replace("-", "_")] = job

    config_jobs = [
        do_deploy.s(job, metadata, app.log.info)
        for job in results
        if isinstance(job, ProvisionResult)
    ]
    callback = end_deploy.s()
    result = chord(config_jobs)(callback)

    for job in result.get():
        if isinstance(job, DeployerResult):
            job.show(msg_cb=app.log.info)


cli.add_command(launch)
