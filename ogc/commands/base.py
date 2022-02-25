import sys
from pathlib import Path

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
            layout.provision(engine)


def start():
    """
    Starts app
    """
    cli()
