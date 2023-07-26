"""ls machines"""
from __future__ import annotations

import click

from ogc.commands.base import cli
from ogc.deployer import ls


@click.command(help="Lists provisioned machines")
@click.option("--query", "-q", "query", help="Filter machines via attributes")
@click.option("--as-yaml", is_flag=True, help="Output as YAML")
@click.option("--as-json", is_flag=True, help="Output as JSON")
def _ls(query: str, as_yaml: bool, as_json: bool) -> None:
    """Lists machines"""
    opts = {}

    if query:
        k, v = query.split("=")
        opts.update({k: v})

    output_format = "table"
    if as_yaml:
        output_format = "yaml"
    if as_json:
        output_format = "json"
    ls(output_format=output_format, **opts)


cli.add_command(_ls, name="ls")
