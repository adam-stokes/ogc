import click
import sh

from .base import cli


@click.command(help="Stream log output")
def log():
    for line in sh.tail("-f", "ogc.log", _iter=True):
        click.secho(line)


cli.add_command(log)
