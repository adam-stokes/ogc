"""Tags model"""
from __future__ import annotations

from peewee import CharField
from playhouse.sqlite_ext import JSONField

from . import BaseModel


class TagModel(BaseModel):
    """Tag Model"""

    class Meta:
        table_name = "tags"

    name = CharField()
    description = CharField(null=True)
    extra = JSONField(null=True)
