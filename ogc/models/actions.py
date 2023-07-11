from __future__ import annotations

import datetime

from attrs import define, field

from .machine import MachineModel


@define
class ActionModel:
    machine: MachineModel
    exit_code: int
    out: str
    err: str
    cmd: str
    created: datetime.datetime = field(init=False)
    extra: dict = field(init=False)

    @property
    def is_failed(self) -> bool:
        """Did action pass or fail"""
        return bool(self.exit_code == 0)

    @created.default
    def get_created(self) -> datetime.datetime:
        return datetime.datetime.utcnow()

    @extra.default
    def get_extra(self) -> dict:
        return {}
