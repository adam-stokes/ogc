import sys
from pathlib import Path

import click
from celery import chord

from ogc import db, log
from ogc.tasks import do_deploy, do_provision, end_provision

from ..provision import DeployerResult, ProvisionResult
from ..spec import SpecLoader
from ..state import app
from .base import cli


@click.command(help="Launches nodes from a provision specification")
@click.option("--spec", required=True, multiple=True)
@click.option(
    "--with-deploy/--with-no-deploy",
    default=True,
    help="Also performs script deployments (default: Yes)",
)
def launch(spec, with_deploy):
    # Db connection
    db.connect()

    specs = []
    # Check for local spec
    if Path("ogc.yml").exists() and not spec:
        specs.append(Path("ogc.yml"))

    for sp in spec:
        _path = Path(sp)
        if not _path.exists():
            log.error(f"Unable to find spec: {sp}")
            sys.exit(1)
        specs.append(_path)
    app.spec = SpecLoader.load(specs)
    log.info(
        f"Provisioning: [{', '.join([layout.name for layout in app.spec.layouts])}]"
    )

    create_jobs = [
        do_provision.s(layout.as_dict(), app.env)
        for layout in app.spec.layouts
        for _ in range(layout.scale)
    ]

    callback = end_provision.s()
    result = chord(create_jobs)(callback)
    results = result.get()

    if with_deploy:
        for job in results:
            do_deploy.delay(job)

    log.info("All tasks have been submitted, please runn `ogc log` to see status output.")


cli.add_command(launch)
