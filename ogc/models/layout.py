"""Layout model"""
from __future__ import annotations

# from attr import define, field
from peewee import CharField, IntegerField
from playhouse.sqlite_ext import JSONField

from . import BaseModel


class LayoutModel(BaseModel):
    """Layout Model

    Synopsis:

    ```python
    from __future__ import annotations

    import typing as t

    from ogc.deployer import Deployer
    from ogc.log import get_logger
    from ogc.models import Layout
    from ogc.provision import choose_provisioner

    log = get_logger("ogc")

    layout = Layout(
        instance_size="e2-standard-4",
        name="ubuntu-ogc",
        provider="google",
        remote_path="/home/ubuntu/ogc",
        runs_on="ubuntu-2004-lts",
        scale=15,
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
    log.debug(layout)

    provisioner = choose_provisioner(layout=layout)
    log.debug(provisioner)

    deploy = Deployer.from_provisioner(provisioner=provisioner)
    log.debug(deploy)


    def up(**kwargs: str) -> None:
        deploy.up()


    def run(**kwargs: str) -> None:
        if kwargs.get("path", None):
            log.info(f"Executing scripts path: {kwargs['path']}")
            deploy.exec_scripts(scripts=kwargs["path"])
        elif kwargs.get("cmd", None):
            log.info(f"Executing command: {kwargs['cmd']}")
            deploy.exec(kwargs["cmd"])
        else:
            log.info(f"Executing scripts path: {layout.scripts}")
            deploy.exec_scripts()


    def down(**kwargs: str) -> None:
        log.info(f"Teardown {deploy} - {kwargs}")
        deploy.down()
    ```
    """

    class Meta:
        table_name = "layouts"

    instance_size = CharField()
    name = CharField()
    provider = CharField()
    remote_path = CharField()
    runs_on = CharField()
    scale = IntegerField()
    scripts = CharField()
    username = CharField()
    ssh_private_key = CharField()
    ssh_public_key = CharField()
    tags = JSONField(null=True)
    labels = JSONField()
    ports = JSONField()
    arch = CharField(null=True)
    exclude = CharField(null=True)
    extra = JSONField(null=True)
    include = CharField(null=True)
