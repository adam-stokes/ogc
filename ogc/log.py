""" debug module
"""

from .state import app
import click


def debug(ctx):
    if app.debug:
        click.secho(f"OGC :: {ctx}", fg="yellow", bold=True)


def error(ctx):
    click.secho(f"OGC :: {ctx}", fg="red", bold=True)


def info(ctx):
    click.secho(f"OGC :: {ctx}", fg="green", bold=True)
