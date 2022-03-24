import click
import sh
from rich import print

from .base import cli


@click.command(help="Stream log output")
def log():
    for line in sh.tail("-f", "ogc.log", _iter=True):
        print(line, end="")


cli.add_command(log)
