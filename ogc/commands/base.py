import click
from click_didyoumean import DYMGroup
from ogc import db

@click.group(cls=DYMGroup)
def cli():
    """Just a simple provisioner"""
    try:
        db.createtbl()
    except:
        pass


def start():
    """
    Starts app
    """
    cli()
