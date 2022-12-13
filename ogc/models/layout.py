"""Layout model"""
from __future__ import annotations

import typing as t
from pathlib import Path

from attr import define, field

from .utils import convert_tags_to_slug_tags


@define
class Layout:
    """Layout model
    
    Synopsis:

    ```python
    from __future__ import annotations

    import typing as t

    import rich.status

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


    def _get_status(**kwargs: str) -> rich.status.Status | None:
        status: "rich.status.Status" | None = t.cast(
            rich.status.Status, kwargs.get("status", None)
        )
        return status


    def up(**kwargs: str) -> None:
        status = _get_status(**kwargs)
        if status:
            status.start()
            status.update(f"Deploying {layout.scale} node(s) for layout: {layout.name}")
            deploy.up()
            status.stop()


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
    instance_size: str
    name: str
    provider: str
    remote_path: str
    runs_on: str
    scale: int
    scripts: str
    username: str
    ssh_private_key: t.LiteralString | Path = field(converter=Path)
    ssh_public_key: t.LiteralString | Path = field(converter=Path)
    tags: list[str] | None = field(converter=convert_tags_to_slug_tags)
    labels: t.Mapping[str, str] | None = None
    ports: list[str] | None = None
    arch: str | None = "amd64"
    artifacts: str | None = None
    exclude: list[str] | None = None
    extra: t.Mapping[str, str] | None = None
    include: list[str] | None = None
