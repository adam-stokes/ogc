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
    from ogc.deployer import init, fs

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
            ssh_private_key=fs.expand_path("~/.ssh/id_rsa_libcloud"),
            ssh_public_key=fs.expand_path("~/.ssh/id_rsa_libcloud.pub"),
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
        > ogc ubuntu.py ls -v
        # Or run a custom task `rerun_scripts`
        > ogc ubuntu.py rerun_scripts -v -o scripts=/a/different/scripts/path
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
