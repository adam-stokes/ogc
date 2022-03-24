import click
import sh

from .base import cli

from rich import print

@click.command(help="Stream log output")
def log():
    for line in sh.tail("-f", "ogc.log", _iter=True):
        print(line, end="")


cli.add_command(log)
