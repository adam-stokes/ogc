from __future__ import annotations

import datetime
import typing as t
from pathlib import Path

from attr import define, field
from libcloud.compute.base import Node as NodeType
from libcloud.compute.ssh import ParamikoSSHClient
from retry import retry

from .actions import Actions
from .layout import Layout
from .utils import get_new_uuid


@define
class Machine:
    remote: NodeType
    layout: Layout
    id: str = field(init=False, factory=get_new_uuid)
    username: str | None = field(init=False)
    ssh_private_key: Path = field(init=False)
    ssh_public_key: Path = field(init=False)
    instance_name: str | None = field(init=False)
    instance_id: str | None = field(init=False)
    instance_state: str | None = field(init=False)
    public_ip: str | None = field(init=False)
    private_ip: str | None = field(init=False)
    created: datetime.datetime = field(init=False, default=datetime.datetime.utcnow())
    extra: t.Mapping | None = None
    tainted: bool = False
    actions: list[Actions] | None = None

    @instance_name.default
    def _get_instance_name(self) -> str:
        return self.remote.name

    @instance_id.default
    def _get_instance_id(self) -> str:
        return str(self.remote.id)

    @instance_state.default
    def _get_instance_state(self) -> str:
        return self.remote.state

    @public_ip.default
    def _get_public_ip(self) -> str:
        return self.remote.public_ips[0]

    @private_ip.default
    def _get_private_ip(self) -> str:
        return self.remote.private_ips[0]

    @username.default
    def _get_username(self) -> str:
        return self.layout.username

    @ssh_private_key.default
    def _get_ssh_private_key(self) -> Path:
        return Path(self.layout.ssh_private_key)

    @ssh_public_key.default
    def _get_ssh_public_key(self) -> Path:
        return Path(self.layout.ssh_public_key)

    @retry(tries=5, delay=5, jitter=(1, 5), logger=None)
    def ssh(self) -> ParamikoSSHClient | None:
        if self.public_ip and self.username:
            _client = ParamikoSSHClient(
                self.public_ip,
                username=self.username,
                key=str(self.ssh_private_key.expanduser()),
                timeout=300,
                use_compression=True,
            )
            _client.connect()
            return _client
        return None

    @classmethod
    def from_layout(cls, layout: Layout, node: NodeType) -> Machine:
        """Grabs the objects for deployment/provision"""
        return Machine(
            layout=layout,
            remote=node,
        )
