import click

from ogc import actions, db
from ogc.deployer import convert_msd_to_actions, is_success
from ogc.log import Logger as log

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
    user = db.get_user().unwrap()
    loaded_spec = SpecLoader.load(list(spec))
    nodes = actions.launch_async(layouts=loaded_spec.layouts, user=user)

    if with_deploy and nodes:
        log.info("Starting script deployments")
        script_deploy_results = actions.deploy_async(nodes=nodes)
        for node in script_deploy_results:
            if is_success(node):
                log.info(f"{node.instance_name}: Deployed Successfully")
            else:
                log.error(f"{node.instance_name}: Failed Deployment")


cli.add_command(launch)
