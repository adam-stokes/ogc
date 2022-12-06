""" action model """
from __future__ import annotations

import datetime
import typing as t

from attr import define, field

from .utils import get_new_uuid


@define
class Actions:
    exit_code: int
    out: str
    error: str
    command: str | None = None
    id: str = field(init=False, factory=get_new_uuid)
    created: datetime.datetime = field(init=False, default=datetime.datetime.utcnow())
    extra: t.Mapping | None = None
