import click
import sh

from .base import cli


@click.command(help="Stream log output")
@click.option(
    "--debug/--no-debug",
    default=False,
    help="Stream debug logging instead",
)
def log(debug):
    logfile = "ogc.log"
    if debug:
        logfile = "ogc.debug.log"    

    for line in sh.tail("-f", logfile, _iter=True, ):
        print(line.rstrip("\n"))


cli.add_command(log)
