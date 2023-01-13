from __future__ import annotations

import datetime

from marshmallow_peewee import ModelSchema
from peewee import DateTimeField, ForeignKeyField, IntegerField, TextField
from playhouse.sqlite_ext import JSONField

from ogc.log import get_logger

from . import BaseModel
from .machine import MachineModel

log = get_logger("ogc")


class ActionModel(BaseModel):
    class Meta:
        table_name = "actions"

    machine = ForeignKeyField(MachineModel, backref="actions", on_delete="CASCADE")
    exit_code = IntegerField(default=0)
    out = TextField(null=True)
    err = TextField(null=True)
    cmd = TextField(null=True)
    created = DateTimeField(default=datetime.datetime.utcnow())
    extra = JSONField(null=True)

    @property
    def is_failed(self) -> bool:
        """Did action pass or fail"""
        return bool(self.exit_code == 0)


class MachineSchema(ModelSchema):
    class Meta:
        model = MachineModel
