from __future__ import annotations

import sys

import arrow
import click
from rich.table import Table

from ogc import db
from ogc.log import CONSOLE as con
from ogc.log import get_logger

from .base import cli

log = get_logger("ogc")


@click.command(help="List nodes in your inventory")
@click.option("--by-tag", required=False, help="List nodes by tag")
@click.option(
    "--by-name",
    required=False,
    help="List nodes by name, this can be a substring match",
)
@click.option(
    "--output-file",
    required=False,
    help="Stores the table output to svg or html. Determined by the file extension.",
)
def ls(by_tag: str, by_name: str, output_file: str) -> None:
    """List current nodes"""
    con.record = True
    if by_tag and by_name:
        log.error(
            "Combined filtered options are not supported, please choose one.",
        )
        sys.exit(1)
    _db = db.Manager()
    _dbrows = _db.nodes()

    rows = _dbrows.values()
    if by_tag:
        rows = [node for node in _dbrows.values() if by_tag in node.layout.tags]
    elif by_name:
        rows = [node for node in _dbrows.values() if node.instance_name == by_name]
    rows_count = len(rows)

    table = Table(
        caption=f"Node Count: [green]{rows_count}[/]",
        header_style="yellow on black",
        caption_justify="left",
        expand=True,
        width=con.width,
        show_lines=True,
    )
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Created")
    table.add_column("Status")
    table.add_column("Labels")
    table.add_column("Connection", style="bold red on black")

    for data in rows:
        table.add_row(
            data.id.split("-")[0],
            data.instance_name,
            arrow.get(data.created).humanize(),
            data.instance_state,
            ",".join([f"[purple]{k}[/]={v}" for k, v in data.layout.labels.items()]),
            f"ssh -i {data.ssh_private_key} {data.username}@{data.public_ip}",
        )

    con.print(table, justify="center")
    if output_file:
        if output_file.endswith("svg"):
            con.save_svg(output_file, title="Node List Output")
        elif output_file.endswith("html"):
            con.save_html(output_file)
        else:
            log.error(
                f"Unknown extension for {output_file}, must end in '.svg' or '.html'"
            )
            sys.exit(1)
    con.record = False


cli.add_command(ls)
