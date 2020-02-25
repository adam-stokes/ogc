# pylint: disable=broad-except

import click
import os

from ..collect import Collector
from ..state import app


@click.group()
def cli():
    pass


@cli.command()
@click.argument("db_key")
@click.argument("db_val")
def set_key(db_key, db_val):
    """ sets db key/val
    """
    JOBID = os.environ['OGC_JOB_ID']
    WORKDIR = os.environ['OGC_JOB_WORKDIR']

    return Collector(JOBID, WORKDIR).setk(db_key, db_val)


@cli.command()
@click.argument("db_key")
def get_key(db_key):
    """ gets db key/val
    """
    JOBID = os.environ['OGC_JOB_ID']
    WORKDIR = os.environ['OGC_JOB_WORKDIR']

    db_val = Collector(JOBID, WORKDIR).getk(db_key)
    click.echo(db_val)


def start():
    """
    Starts app
    """
    cli()
