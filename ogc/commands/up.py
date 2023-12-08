"""provisions machines"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import click
import structlog
import yaml

from ogc import db
from ogc.commands.base import cli
from ogc.deployer import up as d_up
from ogc.models import layout


@click.command(help="Launch machines from layout configurations")
@click.option("--force", is_flag=True, help="Force machine creation")
@click.argument(
    "spec",
    type=click.File("r"),
    metavar="<layouts.yml>",
    required=False,
)
@click.pass_obj
def up(ctx_obj, force: bool, spec: Path | io.TextIOWrapper) -> None:
    """Launches machines from layout specifications by tag"""
    log = structlog.getLogger()
    log.info("Booting up...")
    _machines = db.query()
    if _machines and not force:
        log.info("Machines exist, assuming a re-run.")
        sys.exit(0)

    if not spec:
        log.error("Spec file required.")
        sys.exit(1)

    if spec and isinstance(spec, Path) and not spec.exists():
        log.error(
            f"Unable to locate {spec} and no existing machines are deployed, please double check the path."
        )
        sys.exit(1)

    layouts_from_spec = None
    if isinstance(spec, io.TextIOWrapper):
        layouts_from_spec = yaml.safe_load(spec.read())
    else:
        layouts_from_spec = yaml.safe_load(spec.read_text())
    layouts_from_spec = layout.LayoutModel.create_from_specs(
        layouts_from_spec["layouts"]
    )

    d_up(layouts_from_spec)


cli.add_command(up, name="up")
