import datetime
import os
import uuid
from pathlib import Path
from typing import Iterator

import toolz
from attr import define, field
from dotenv import dotenv_values
from libcloud.compute.base import Node as NodeType
from libcloud.compute.deployment import MultiStepDeployment
from slugify import slugify


@define
class Layout:
    instance_size: str
    name: str
    provider: str
    remote_path: str
    runs_on: str
    scale: int
    scripts: str
    username: str
    ssh_private_key: Path
    ssh_public_key: Path
    tags: list[str] = field()
    ports: list[str] = field()
    arch: str = field(init=False, default="amd64")
    artifacts: str = field(default=None)
    exclude: list[str] = field(factory=list)
    extra: dict = field(init=False, factory=dict)
    include: list[str] = field(factory=list)
    id: str = field(init=False, default=str(uuid.uuid4()))

    @tags.default
    def _get_tags(self) -> list[str]:
        return [slugify(tag) for tag in self.tags]

    @ports.default
    def _get_ports(self) -> list[str]:
        return self.ports or list()


@define
class Plan:
    layouts: list[Layout]
    name: str
    ssh_keys: dict[str, Path]
    id: str = field(init=False, default=str(uuid.uuid4()))

    def get_layout(self, name: str) -> list[Layout]:
        return list(toolz.filter(lambda x: x.name == name, self.layouts))


@define
class User:
    name: str
    slug: str = field(init=False)
    id: str = field(init=False, default=str(uuid.uuid4()))
    created: datetime.datetime = field(init=False, default=datetime.datetime.utcnow())
    env: dict = field(init=False)

    @env.default
    def _get_env(self) -> dict:
        return {**dotenv_values(".env"), **os.environ}

    @slug.default
    def _get_slug(self) -> str:
        return f"user-{slugify(self.name)}"


@define
class Node:
    node: NodeType
    layout: Layout
    user: User
    spec: Plan = field(init=False, default=None)
    id: str = field(init=False, default=str(uuid.uuid4()))
    instance_name: str = field(init=False)
    instance_id: str = field(init=False)
    instance_state: str = field(init=False)
    public_ip: str = field(init=False)
    private_ip: str = field(init=False)
    created: datetime.datetime = field(init=False, default=datetime.datetime.utcnow())
    extra: dict = field(init=False, factory=dict)

    @instance_name.default
    def _get_instance_name(self) -> str:
        return self.node.name

    @instance_id.default
    def _get_instance_id(self) -> str:
        return self.node.id

    @instance_state.default
    def _get_instance_state(self) -> str:
        return self.node.state

    @public_ip.default
    def _get_public_ip(self) -> str:
        return self.node.public_ips[0]

    @private_ip.default
    def _get_private_ip(self) -> str:
        return self.node.private_ips[0]


@define
class Actions:
    exit_code: int
    out: str
    error: str
    node: Node
    command: str = field(init=False, default=str)
    id: str = field(init=False, default=str(uuid.uuid4()))
    created: datetime.datetime = field(init=False, default=datetime.datetime.utcnow())
    extra: dict = field(init=False, factory=dict)


@define
class DeployResult:
    node: Node
    msd: MultiStepDeployment
    id: str = field(init=False, default=str(uuid.uuid4()))
