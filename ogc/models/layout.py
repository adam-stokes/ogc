"""Layout model"""
from __future__ import annotations

import random
import string

from attr import define, field


@define
class LayoutModel:
    """Layout Model

    ```python
    layout_model=dict(
        instance_size="e2-standard-4",
        provider="google",
        remote_path="/home/ubuntu",
        runs_on="ubuntu-2204-lts",
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
    name: str = field(init=False)

    @classmethod
    def create_from_specs(cls, specs: list) -> list[LayoutModel]:
        """Creates layout objects from spec file"""
        return [LayoutModel(**spec) for spec in specs]

    @name.default
    def get_name(self) -> str:
        alphabet = string.ascii_lowercase + string.digits
        return f"ogc-layout-{''.join(random.choices(alphabet, k=8))}"
