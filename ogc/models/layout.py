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
            scale=9,
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

    def rerun_scripts(**kwargs: str):
        deployment.exec_scripts(**kwargs)
    ```

    Example:
        ```bash
        > docker run --env-file .env --rm --volumes-from gcloud-config -v `pwd`:`pwd` -w `pwd` -it ogc:latest ogc fixtures/layouts/ubuntu ls -v
        # Or run a custom task `hithere`
        > docker run --env-file .env --rm --volumes-from gcloud-config -v `pwd`:`pwd` -w `pwd` -it ogc:latest ogc fixtures/layouts/ubuntu rerun_scripts -v -o scripts=/a/different/scripts/path
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
