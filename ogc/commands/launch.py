import click

from ogc import actions, db
from ogc.provision import save_result
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
    user.spec = SpecLoader.load(list(spec))
    nodes = actions.launch_async(layouts=user.spec.layouts, config=user)
    if with_deploy and nodes:
        log.info("Starting script deployments")
        script_deploy_results = actions.deploy_async(nodes=nodes, config=user)
        if all(
            result
            for result in script_deploy_results
            if script_deploy_results and result.instance_state == "running"
        ):
            log.info("All deployments have been completed, recording results.")
            save_result(list(script_deploy_results), config=user)
            return
        log.error("Some tasks could not be completed.")


cli.add_command(launch)
