import click
from click_didyoumean import DYMGroup


@click.group(cls=DYMGroup)
def cli():
    pass


def start():
    """
    Starts app
    """
    cli()
