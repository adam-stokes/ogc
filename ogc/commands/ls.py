"""ls machines"""
from __future__ import annotations

import click

from ogc.commands.base import cli
from ogc.deployer import ls


@click.command(help="Lists provisioned machines")
@click.option("--as-list", is_flag=True, help="Output as simple list")
@click.option("--as-yaml", is_flag=True, help="Output as YAML")
@click.option("--as-json", is_flag=True, help="Output as JSON")
@click.pass_obj
def _ls(ctx_obj, as_yaml: bool, as_json: bool, as_list: bool) -> None:
    """Lists machines"""
    output_format = "table"
    if as_yaml:
        output_format = "yaml"
    if as_json:
        output_format = "json"
    if as_list:
        output_format = "list"
    ls(output_format=output_format, **ctx_obj.opts)


cli.add_command(_ls, name="ls")
