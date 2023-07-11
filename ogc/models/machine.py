from __future__ import annotations

import datetime
from pathlib import Path

import paramiko.ssh_exception
from attrs import define, field
from libcloud.compute.base import Node
from libcloud.compute.ssh import ParamikoSSHClient
from retry import retry

from ogc import db
from ogc.log import get_logger

from .layout import LayoutModel

log = get_logger("ogc")


@define
class MachineModel:
    layout: LayoutModel = field()
    node: Node = field()
    created: datetime.datetime = field(init=False)
    instance_name: str = field(init=False)
    instance_id: str = field(init=False)
    public_ip: str = field(init=False)
    private_ip: str = field(init=False)

    @instance_name.default
    def get_instance_name(self) -> str:
        return self.node.name

    @instance_id.default
    def get_instance_id(self) -> str:
        return self.node.id

    @public_ip.default
    def get_public_ip(self) -> str:
        return self.node.public_ips[0]

    @private_ip.default
    def get_private_ip(self) -> str:
        return self.node.private_ips[0]

    @created.default
    def get_created(self) -> datetime.datetime:
        return datetime.datetime.utcnow()

    @retry(tries=5, delay=5, jitter=(1, 5), logger=None)
    def ssh(self) -> ParamikoSSHClient | None:
        """Provides an SSH Client for use with provisioning"""
        priv_key = Path(self.layout.ssh_private_key).expanduser().resolve()
        if self.node.public_ips[0] and self.layout.username:
            _client = ParamikoSSHClient(
                str(self.node.public_ips[0]),
                username=str(self.layout.username),
                key=str(priv_key),
                timeout=300,
                use_compression=True,
            )
            try:
                _client.connect()
            except paramiko.ssh_exception.SSHException:
                log.error(
                    f"Authentication failed for: ({self.layout.name}/{priv_key}) {self.layout.username}@{self.node.public_ips[0]}"
                )
                return None
            return _client
        return None

    @classmethod
    def query(cls, **kwargs: str) -> list[MachineModel]:
        """list layouts"""
        cache = db.cache_path()
        _machines = [
            db.pickle_to_model(cache.get(machine)) for machine in cache.iterkeys()
        ]
        _filtered_machines: list[MachineModel] = []
        if kwargs:
            for k, v in kwargs.items():
                for _machine in _filtered_machines:
                    if getattr(_machine, k) == v:
                        _filtered_machines.append(_machine)
        if _filtered_machines:
            return _filtered_machines
        return _machines
