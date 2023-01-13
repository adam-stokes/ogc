"""init"""
from __future__ import annotations

from peewee import *

from ..db import connect

db = connect()


class BaseModel(Model):
    """Base db model"""

    class Meta:
        database = db
