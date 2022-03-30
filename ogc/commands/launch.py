from pathlib import Path

import click

from ogc.actions import deploy as deploy_p
from ogc.actions import launch as launch_p
from ogc.log import Logger as log

from ..spec import SpecLoader
from ..state import app
from .base import cli


@click.command(help="Launches nodes from a provision specification")
@click.option("--spec", required=False, multiple=True)
@click.option(
    "--with-deploy/--with-no-deploy",
    default=True,
    help="Also performs script deployments (default: Yes)",
)
def launch(spec, with_deploy):
    # Db connection
    app.spec = SpecLoader.load(list(spec))
    log.info(f"Provisioning: {', '.join([layout.name for layout in app.spec.layouts])}")
    node_ids = launch_p(app.spec.layouts)

    if with_deploy:
        deploy_p(node_ids)

    log.info(
        "All tasks have been submitted, please run `ogc log` to see status output."
    )


cli.add_command(launch)
