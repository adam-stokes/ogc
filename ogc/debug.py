""" debug module
"""

from .state import app
import click


def debug(ctx):
    if app.config["debug"]:
        click.echo(f"Debug :: {ctx}")
