"""init"""
from __future__ import annotations

import datetime
import uuid
from pathlib import Path

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
