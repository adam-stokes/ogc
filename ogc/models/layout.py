"""Layout model"""
from __future__ import annotations

import typing as t
from pathlib import Path

from attr import define, field

from .utils import convert_tags_to_slug_tags


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
