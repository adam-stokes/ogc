import click

from ogc import actions

from ..spec import SpecLoader
from .base import cli


@click.command(help="Launches nodes from a provision specification")
@click.option("--spec", required=False, multiple=True)
@click.option(
    "--with-deploy/--with-no-deploy",
    default=True,
    help="Also performs script deployments",
)
def launch(spec: list[str], with_deploy: bool) -> None:
    # Application Config
    loaded_spec = SpecLoader.load(list(spec))
    actions.launch_async(layouts=loaded_spec.layouts, with_deploy=with_deploy)


cli.add_command(launch)
