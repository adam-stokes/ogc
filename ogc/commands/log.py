import click
import sh
from rich.console import Console

from .base import cli


@click.command(help="Stream log output")
def log():
    console = Console()
    for line in sh.tail("-f", "ogc.log", _iter=True):
        console.log(line.rstrip("\n"), markup=True, end="")


cli.add_command(log)
