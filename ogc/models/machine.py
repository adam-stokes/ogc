from __future__ import annotations

import datetime
from pathlib import Path

import paramiko.ssh_exception
from libcloud.compute.base import Node
from libcloud.compute.ssh import ParamikoSSHClient
from marshmallow_peewee import ModelSchema
from peewee import BooleanField, CharField, DateTimeField, ForeignKeyField
from playhouse.sqlite_ext import JSONField
from retry import retry

from ogc.log import get_logger

from ..db import pickle_to_model
from . import BaseModel
from .layout import LayoutModel

log = get_logger("ogc")


class MachineModel(BaseModel):
    class Meta:
        table_name = "machines"

    layout = ForeignKeyField(LayoutModel, backref="machines", on_delete="CASCADE")
    instance_name = CharField()
    instance_id = CharField()
    instance_state = CharField()
    public_ip = CharField()
    private_ip = CharField()
    created = DateTimeField(default=datetime.datetime.utcnow())
    extra = JSONField(null=True)
    tainted = BooleanField(default=False)
    remote_state_file = CharField(null=True)

    def state(self) -> Node | None:
        """Returns the store remote state of a node in the cloud"""
        state_file_p = Path(str(self.remote_state_file))
        if state_file_p.exists():
            out: Node = pickle_to_model(state_file_p.read_bytes())
            return out
        return None

    @retry(tries=5, delay=5, jitter=(1, 5), logger=None)
    def ssh(self) -> ParamikoSSHClient | None:
        """Provides an SSH Client for use with provisioning"""
        priv_key = Path(self.layout.ssh_private_key).expanduser().resolve()
        if self.public_ip and self.layout.username:
            _client = ParamikoSSHClient(
                str(self.public_ip),
                username=str(self.layout.username),
                key=str(priv_key),
                timeout=300,
                use_compression=True,
            )
            try:
                _client.connect()
            except paramiko.ssh_exception.SSHException:
                log.error(
                    f"Authentication failed for: ({self.layout.name}/{priv_key}) {self.layout.username}@{self.public_ip}"
                )
                return None
            return _client
        return None


class MachineSchema(ModelSchema):
    class Meta:
        model = MachineModel
