"""layout spec"""

from __future__ import annotations

from ogc.deployer import Deployer
from ogc.log import get_logger
from ogc.models import Layout
from ogc.provision import choose_provisioner
from ogc.signals import after_provision, ready_provision, ready_teardown

log = get_logger("ogc")

layout = Layout(
    instance_size="e2-standard-4",
    name="ubuntu-ogc",
    provider="google",
    remote_path="/home/ubuntu/ogc",
    runs_on="ubuntu-2004-lts",
    scale=1,
    scripts="fixtures/ex_deploy_ubuntu",
    username="ubuntu",
    ssh_private_key="~/.ssh/id_rsa_libcloud",
    ssh_public_key="~/.ssh/id_rsa_libcloud.pub",
    ports=["22:22", "80:80", "443:443", "5601:5601"],
    tags=[],
    labels=dict(
        division="engineering", org="obs", team="observability", project="perf"
    ),
)

provisioner = choose_provisioner(layout=layout)
deploy = Deployer.from_provisioner(provisioner=provisioner)


@ready_provision.connect
def start(sender) -> None:
    log.debug(layout)
    deploy.up()

    if "with_deploy" in sender and sender["with_deploy"]:
        log.info("Executing scripts")
        deploy.exec_scripts()

    log.debug(deploy)


@ready_teardown.connect
def end(sender) -> None:
    provisioner = choose_provisioner(layout=layout)
    deploy = Deployer.from_provisioner(provisioner=provisioner)
    log.debug(f"Teardown {deploy} - {sender}")
    deploy.down()


@after_provision.connect
def do(sender) -> None:
    provisioner = choose_provisioner(layout=layout)
    deploy = Deployer.from_provisioner(provisioner=provisioner)
    if "cmd" in sender and sender["cmd"]:
        deploy.exec(sender["cmd"])
    elif "path" in sender and sender["path"]:
        deploy.exec_scripts(scripts=sender["path"])
    else:
        deploy.exec_scripts()
