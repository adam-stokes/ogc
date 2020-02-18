# pylint: disable=broad-except

import click

from ..collect import Collector


@click.group()
def cli():
    pass

@cli.command()
@click.argument("db_key")
@click.argument("db_val")
def set_key(db_key, db_val):
    """ sets db key/val
    """
    Collector().setk(db_key, db_val)


@cli.command()
@click.argument("db_key")
def get_key(db_key):
    """ gets db key/val
    """
    db_val = Collector().getk(db_key)
    click.echo(db_val)


def start():
    """
    Starts app
    """
    cli()
