from __future__ import annotations

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


def serialize(inst: str, field: str, value: str | datetime.datetime | Path) -> str:
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def convert_tags_to_slug_tags(tags: list[str] | None) -> list[str] | None:
    """Converts tags to their slugged equivalent"""
    if tags:
        return [slugify(tag) for tag in tags]
    return None


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
    tags: list[str] | None = field(converter=convert_tags_to_slug_tags)
    labels: t.Mapping[str, str] | None = None
    ports: list[str] | None = None
    arch: str | None = "amd64"
    artifacts: str | None = None
    exclude: list[str] | None = None
    extra: t.Mapping[str, str] | None = None
    include: list[str] | None = None
    id: str = field(init=False, factory=get_new_uuid)

    def env(self) -> Dotty:
        return dotty({**dotenv_values(".env"), **os.environ})


@define
class Plan:
    layouts: list[Layout]
    name: str
    ssh_keys: t.Mapping[str, Path]
    id: str = field(init=False, factory=get_new_uuid)

    def get_layout(self, name: str) -> list[Layout]:
        return list(toolz.filter(lambda x: x.name == name, self.layouts))


@define
class Actions:
    exit_code: int
    out: str
    error: str
    command: str | None = None
    id: str = field(init=False, factory=get_new_uuid)
    created: datetime.datetime = field(init=False, default=datetime.datetime.utcnow())
    extra: t.Mapping | None = None


@define
class Node:
    node: NodeType
    layout: Layout
    actions: list[Actions] | None = None
    id: str = field(init=False, factory=get_new_uuid)
    instance_name: str | None = field(init=False)
    instance_id: str | None = field(init=False)
    instance_state: str | None = field(init=False)
    public_ip: str | None = field(init=False)
    private_ip: str | None = field(init=False)
    created: datetime.datetime = field(init=False, default=datetime.datetime.utcnow())
    extra: t.Mapping | None = None
    tainted: bool = False

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
