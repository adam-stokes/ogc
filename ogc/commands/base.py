import sys
from pathlib import Path
from pprint import pprint

import click

from ..provision import choose_provisioner
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

    for provider, options in app.spec.providers.items():
        engine = choose_provisioner(provider, options, app.env)
        app.log.info(f"Using provisioner: {engine}")
        for layout in app.spec.layouts:
            if layout.providers and provider not in layout.providers:
                app.log.debug(f"Skipping excluded layout: {layout}")
                continue
            app.log.info(f"Deploying {layout}")
            node, steps = engine.deploy(layout, app.spec.ssh)
            app.log.info(f"Launched {node.name} [{node.state}]")
            app.log.info(f"  Provision Result:")
            for step in steps.steps:
                app.log.info(f"  - [{step.exit_status}]: {step}")


def start():
    """
    Starts app
    """
    cli()
