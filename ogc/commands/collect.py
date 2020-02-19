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


@cli.command()
@click.option(
    "--profile-name", required=True, help="AWS profile to use", default="default"
)
@click.option(
    "--region-name", required=True, help="AWS region to use", default="us-east-1"
)
@click.option("--bucket", required=True, help="s3 bucket to use", default="jenkaas")
@click.argument("db_key")
@click.argument("results-file", nargs=-1)
def push(profile_name, region_name, bucket, db_key, results_file):
    collect = Collector()
    collect.push(profile_name, region_name, bucket, db_key, results_file)


def start():
    """
    Starts app
    """
    cli()
