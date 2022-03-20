import click


@click.group()
def cli():
    from ..tasks import do_provision
    do_provision.delay()
    pass


def start():
    """
    Starts app
    """
    cli()
