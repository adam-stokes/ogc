import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import click

from ogc import actions
from ogc.log import Logger as log

from ..spec import SpecLoader
from ..state import app
from .base import ogc as cli


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
    node_ids = actions.launch_async(app.spec.layouts)
    if with_deploy:
        log.info(f"Starting script deployments")
        script_deploy_results = actions.deploy_async(node_ids)
        if all(result == True for result in script_deploy_results):
            log.info("All deployments have been completed.")
            return
        log.error("Some tasks could not be completed.")


cli.add_command(launch)
