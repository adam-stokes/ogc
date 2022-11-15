import datetime
import os
import typing as t
import uuid
from pathlib import Path

import toolz
from attr import define, field
from dotenv import dotenv_values
from dotty_dict import Dotty, dotty
from libcloud.compute.base import Node as NodeType
from slugify import slugify


def get_new_uuid() -> str:
    return str(uuid.uuid1())


def serialize(inst, field, value):
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


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
    tags: t.Optional[list[str]] = field()
    ports: t.Optional[list[str]] = field()
    arch: t.Optional[str] = "amd64"
    artifacts: t.Optional[str] = None
    exclude: t.Optional[list[str]] = None
    extra: t.Optional[t.Mapping[str, str]] = {}
    include: t.Optional[list[str]] = None
    id: str = field(init=False, factory=get_new_uuid)

    @tags.default
    def _get_tags(self) -> list[str]:
        return [slugify(tag) for tag in self.tags]

    @ports.default
    def _get_ports(self) -> list[str]:
        return self.ports or list()

    def env(self) -> Dotty:
        return dotty({**dotenv_values(".env"), **os.environ})


@define
class Plan:
    layouts: list[Layout]
    name: str
    ssh_keys: dict[str, Path]
    id: str = field(init=False, factory=get_new_uuid)

    def get_layout(self, name: str) -> list[Layout]:
        return list(toolz.filter(lambda x: x.name == name, self.layouts))


@define
class Actions:
    exit_code: int
    out: str
    error: str
    command: t.Optional[str] = None
    id: str = field(init=False, factory=get_new_uuid)
    created: datetime.datetime = field(init=False, default=datetime.datetime.utcnow())
    extra: dict = field(init=False, factory=dict)


@define
class Node:
    node: NodeType
    layout: Layout
    actions: t.Optional[list[Actions]] = None
    id: str = field(init=False, factory=get_new_uuid)
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
        return str(self.node.id)

    @instance_state.default
    def _get_instance_state(self) -> str:
        return self.node.state

    @public_ip.default
    def _get_public_ip(self) -> str:
        return self.node.public_ips[0]

    @private_ip.default
    def _get_private_ip(self) -> str:
        return self.node.private_ips[0]
