import click
from click_didyoumean import DYMGroup


@click.group(cls=DYMGroup)
def cli() -> None:
    """Just a simple provisioner"""
    pass


def start() -> None:
    """
    Starts app
    """
    cli()
