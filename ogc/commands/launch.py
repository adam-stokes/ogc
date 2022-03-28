import sys
from pathlib import Path

import click
from rich.console import Console

from ogc import log
from ogc.actions import deploy as deploy_p
from ogc.actions import launch as launch_p

from ..spec import SpecLoader
from ..state import app
from .base import cli

console = Console()

@click.command(help="Launches nodes from a provision specification")
@click.option("--spec", required=False, multiple=True)
@click.option(
    "--with-deploy/--with-no-deploy",
    default=True,
    help="Also performs script deployments (default: Yes)",
)
def launch(spec, with_deploy):
    # Db connection
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

    if not specs:
        log.error("No provision specs found, please specify with `--spec <file.yml>`")
        sys.exit(1)

    app.spec = SpecLoader.load(specs)
    console.log(f"Provisioning: {', '.join([layout.name for layout in app.spec.layouts])}")
    node_ids = launch_p(app.spec.layouts, app.env)

    if with_deploy:
        deploy_p(node_ids)

    console.log(
        "All tasks have been submitted, please run `ogc log` to see status output."
    )


cli.add_command(launch)
