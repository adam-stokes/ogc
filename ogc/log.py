""" debug module
"""

from .state import app
import click
from datetime import datetime


def debug(ctx):
    if app.debug:
        click.secho(
            f"[{datetime.now().strftime('%H:%M:%S')}] OGC :: {ctx}",
            fg="yellow",
            bold=True,
        )


def error(ctx):
    click.secho(
        f"[{datetime.now().strftime('%H:%M:%S')}] OGC :: {ctx}", fg="red", bold=True
    )


def info(ctx):
    click.secho(
        f"[{datetime.now().strftime('%H:%M:%S')}] OGC :: {ctx}", fg="green", bold=True
    )
