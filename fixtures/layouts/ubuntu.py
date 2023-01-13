"""layout spec"""

from __future__ import annotations

from ogc.deployer import init
from ogc.fs import expand_path
from ogc.log import get_logger

log = get_logger("ogc")

deployment = init(
    layout_model=dict(
        instance_size="e2-standard-4",
        name="ubuntu-ogc",
        provider="google",
        remote_path="/home/ubuntu/ogc",
        runs_on="ubuntu-2004-lts",
        scale=2,
        scripts="fixtures/ex_deploy_ubuntu",
        username="ubuntu",
        ssh_private_key=expand_path("~/.ssh/id_rsa_libcloud"),
        ssh_public_key=expand_path("~/.ssh/id_rsa_libcloud.pub"),
        ports=["22:22", "80:80", "443:443", "5601:5601"],
        tags=[],
        labels=dict(
            division="engineering", org="obs", team="observability", project="perf"
        ),
    ),
)


# provisioner = choose_provisioner(layout=layout)
# deploy = Deployer.from_provisioner(provisioner=provisioner)
# deploy.up()
# log.info(f"Executing custom scripts path: {kwargs['path']}")
# deploy.exec_scripts(scripts=kwargs["path"])
# log.info(f"Executing command: {kwargs['cmd']}")
# deploy.exec(kwargs["cmd"])
# log.info(f"Executing scripts path: {layout.scripts}")
# deploy.exec_scripts()
# log.info(f"Teardown {layout.machines.count()} machine(s)")
# deploy.down()
# layout.delete_instance()
