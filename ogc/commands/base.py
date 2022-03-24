import click
from click_didyoumean import DYMGroup


@click.group(cls=DYMGroup)
def cli():
    """Just a simple provisioner"""


def start():
    """
    Starts app
    """
    cli()
