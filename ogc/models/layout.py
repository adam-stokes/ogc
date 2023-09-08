"""Layout model"""
from __future__ import annotations

from attr import define, field


@define
class LayoutModel:
    """Layout Model

    ```python
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
    ```
    """

    instance_size: str = field()
    name: str = field()
    provider: str = field()
    remote_path: str = field()
    runs_on: str = field()
    scale: int = field()
    username: str = field()
    ssh_private_key: str = field()
    ssh_public_key: str = field()
    tags: list[str] = field()
    labels: dict = field()
    ports: dict = field()

    @classmethod
    def create_from_specs(cls, specs: list) -> list[LayoutModel]:
        """Creates layout objects from spec file"""
        return [LayoutModel(**spec) for spec in specs]
