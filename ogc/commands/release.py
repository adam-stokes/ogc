""" Tracks the progress of a release through it's different stages
"""
import click
from .base import cli
from .. import api
import argparse
import boto3
import sys


@click.group()
@click.option("--identifier", required=True, help="Tracking identification")
@click.pass_context
def release(ctx, identifier):
    ctx.ensure_object(dict)

    session = boto3.Session(region_name="us-east-1")
    dynamodb = session.resource("dynamodb")
    table = dynamodb.Table("ReleaseTracker")
    ctx["table"] = table

    response = table.get_item(Key={"release_id": identifier})
    if response and "Item" in response:
        ctx["db"] = response["Item"]
    else:
        ctx["db"]["release_id"] = identifier


@click.command()
@click.option("--name", required=True, help="Name of phase")
@click.option("--result", required=True, type=click.Choice(["pass", "fail", "timeout"]))
@click.pass_context
def set_phase(ctx, name, result):
    return api.release.set_phase(ctx["table"], ctx["db"], name, result)


@click.option("--name", required=True, help="Name of phase")
@click.pass_context
def get_phase(ctx, name):
    return api.release.get_phase(ctx["db"], name)


cli.add_command(release)
release.add_command(set_phase)
release.add_command(get_phase)
