""" debug module
"""

from .state import app
import click


def debug(ctx):
    if app.debug:
        click.echo(click.style(f"OGC :: debug :: {ctx}", fg='yellow'))
