# pylint: disable=wrong-import-position
# pylint: disable=wrong-import-order

from __future__ import annotations

import datetime
import os
import typing as t
import uuid
from pathlib import Path

from libcloud.common.google import ResourceNotFoundError
from libcloud.compute.base import (
    KeyPair,
    Node,
    NodeAuthSSHKey,
    NodeDriver,
    NodeImage,
    NodeLocation,
    NodeSize,
)
from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider
from retry import retry

from ogc import db, signals
from ogc.enums import CLOUD_IMAGE_MAP
from ogc.exceptions import ProvisionException
from ogc.log import get_logger
from ogc.models.layout import LayoutModel
from ogc.models.machine import MachineModel

log = get_logger("ogc")


class BaseProvisioner:
    """Base provisioner"""

    def __init__(self, layout: LayoutModel):
        self.layout: LayoutModel = layout
        self.env: t.Mapping[str, str] = os.environ.copy()
        self.provisioner: NodeDriver | None = None

    @classmethod
    def from_layout(cls, layout: LayoutModel, connect: bool = True) -> BaseProvisioner:
        _prov = (
            GCEProvisioner(layout=layout)
            if layout.provider == "google"
            else AWSProvisioner(layout=layout)
        )
        if connect:
            _prov.provisioner = _prov.connect()
        return _prov

    @property
    def options(self) -> t.Mapping[str, str]:
        raise NotImplementedError()

    def connect(self) -> NodeDriver:
        raise NotImplementedError()

    def create(self) -> list[MachineModel] | None:
        raise NotImplementedError()

    def setup(self) -> None:
        """Perform some provider specific setup before launch"""
        raise NotImplementedError()

    def cleanup(self, node: MachineModel, **kwargs: dict[str, object]) -> bool:
        """Perform some provider specific cleanup after node destroy typically"""
        raise NotImplementedError()

    def destroy(self, nodes: list[MachineModel]) -> bool:
        for node in nodes:
            if node.remote_state_file:
                self.provisioner.destroy_node(node.state())
        return True

    def node(self, **kwargs: t.Mapping[str, t.Union[str, object]]) -> Node | None:
        raise NotImplementedError()

    def sizes(self, instance_size: str) -> list[NodeSize]:
        _sizes = self.provisioner.list_sizes()
        try:
            return [
                size
                for size in _sizes
                if size.id == instance_size or size.name == instance_size
            ]
        except IndexError:
            raise ProvisionException(
                f"Could not locate instance size for {instance_size}"
            )

    def image(self, runs_on: str) -> NodeImage:
        """Gets a single image from registry of provider"""
        return self.provisioner.get_image(runs_on)

    def images(self, location: t.Optional[NodeLocation] = None) -> list[NodeImage]:
        return self.provisioner.list_images(location)

    @retry(delay=5, jitter=(1, 5), tries=5, logger=None)
    def _create_node(self, **kwargs: dict[str, object]) -> MachineModel:
        _opts = kwargs.copy()
        node = self.provisioner.create_node(**_opts)  # type: ignore
        node = self.provisioner.wait_until_running(
            nodes=[node], wait_period=5, timeout=300
        )[0][0]
        if not node.id:
            node.id = str(uuid.uuid4())
        state_file_p = db.cache_path() / node.id
        state_file_p.write_bytes(db.model_as_pickle(node))
        machine = MachineModel(
            layout=self.layout,
            instance_name=node.name,
            instance_id=node.id,
            instance_state=node.state,
            public_ip=node.public_ips[0],
            private_ip=node.private_ips[0],
            remote_state_file=(db.cache_path() / node.id).resolve(),
        )
        return machine

    def list_nodes(self, **kwargs: dict[str, object]) -> list[Node]:
        return self.provisioner.list_nodes(**kwargs)

    def create_keypair(self, name: str, ssh_public_key: str) -> KeyPair:
        return self.provisioner.import_key_pair_from_file(
            name=name, key_file_path=ssh_public_key
        )

    def get_key_pair(self, name: str) -> KeyPair:
        return self.provisioner.get_key_pair(name)

    @retry(delay=5, jitter=(1, 5), tries=15, logger=None)
    def delete_key_pair(self, key_pair: KeyPair) -> bool:
        return self.provisioner.delete_key_pair(key_pair)

    def list_key_pairs(self) -> list[KeyPair]:
        return self.provisioner.list_key_pairs()

    def _userdata(self) -> str:
        """Some instances on AWS do not include rsync which is needed for file transfers"""
        return """#!/usr/bin/env bash
if ! test -f "/usr/local/bin/pacapt"; then
    sudo wget -O /usr/local/bin/pacapt https://github.com/icy/pacapt/raw/ng/pacapt
    sudo chmod 755 /usr/local/bin/pacapt
    sudo ln -sv /usr/local/bin/pacapt /usr/local/bin/pacman || true
fi
pacapt update || true
pacapt install rsync || true
"""


class AWSProvisioner(BaseProvisioner):
    """AWS Provisioner

    Required Environment Variables:

        - **AWS_ACCESS_KEY_ID**
        - **AWS_SECRET_ACCESS_KEY**

    Optional Environment Variables:

        - **AWS_REGION**
    """

    @property
    def options(self) -> t.Mapping[str, str]:
        return {
            "key": self.env.get("AWS_ACCESS_KEY_ID", ""),
            "secret": self.env.get("AWS_SECRET_ACCESS_KEY", ""),
            "region": self.env.get("AWS_REGION", "us-east-2"),
        }

    @retry(delay=5, tries=10, jitter=(5, 25), logger=None)
    def connect(self) -> NodeDriver:
        aws = get_driver(Provider.EC2)
        return aws(**self.options)

    def setup(self) -> None:
        if self.layout.ports:
            self.create_firewall(self.layout.name, self.layout.ports)
        if not any(kp.name == self.layout.name for kp in self.list_key_pairs()):
            self.create_keypair(self.layout.name, str(self.layout.ssh_public_key))

    def cleanup(self, node: Node, **kwargs: dict[str, object]) -> bool:
        pass

    def image(self, runs_on: str) -> NodeImage:
        if runs_on.startswith("ami-"):
            _runs_on: str = runs_on
        else:
            # FIXME: need proper architecture detection
            _runs_on = CLOUD_IMAGE_MAP["aws"]["amd64"].get(runs_on, "")
        return super().image(_runs_on)

    def create_firewall(self, name: str, ports: list[str]) -> None:
        """Creates the security group for enabling traffic between nodes"""
        if not any(sg.name == name for sg in self.provisioner.ex_get_security_groups()):  # type: ignore
            self.provisioner.ex_create_security_group(name, "ogc sg", vpc_id=None)  # type: ignore

        for port in ports:
            ingress, egress = port.split(":")
            self.provisioner.ex_authorize_security_group(  # type: ignore
                name, ingress, egress, "0.0.0.0/0", "tcp"
            )

    def delete_firewall(self, name: str) -> None:
        pass

    def create(self) -> list[MachineModel] | None:
        pub_key = Path(self.layout.ssh_public_key).expanduser().read_text()
        auth = NodeAuthSSHKey(pub_key)
        image = self.image(self.layout.runs_on)
        if not image and not self.layout.username:
            raise ProvisionException(
                f"Could not locate AMI and/or username for: {self.layout.runs_on}"
            )

        size = self.sizes(self.layout.instance_size)[0]

        opts = dict(
            name=f"{str(uuid.uuid4())[:8]}-{self.layout.name}",
            image=image,
            size=size,
            auth=auth,
            ex_securitygroup=self.layout.name,
            ex_spot=True,
            ex_maxcount=self.layout.scale,
            ex_userdata=self._userdata()
            if "windows" not in self.layout.runs_on
            else "",
            ex_terminate_on_shutdown=True,
        )
        tags = {}

        # Store some metadata for helping with cleanup
        now = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        if self.layout.tags:
            self.layout.tags.append(now)
            self.layout.tags.append(f"user-{os.environ.get('USER', 'ogc')}")
            tags["created"] = now
            tags["user_tag"] = f"user-{os.environ.get('USER', 'ogc')}"
            # Store some extra metadata similar to what other projects use
            epoch = str(datetime.datetime.now().timestamp())
            tags["created_date"] = epoch
            tags["environment"] = "ogc"
            tags["repo"] = "ogc"

        node = self.provisioner.create_node(**opts)  # type: ignore
        _machines = []
        state_file_p = db.cache_path() / node.id
        state_file_p.write_bytes(db.model_as_pickle(node))
        machine = MachineModel(
            layout=self.layout,
            instance_name=node.name,
            instance_id=node.id,
            instance_state=node.state,
            public_ip=node.public_ips[0],
            private_ip=node.private_ips[0],
            remote_state_file=(db.cache_path() / node.id).resolve(),
        )
        machine.save()
        _machines.append(machine)
        return _machines if _machines else None

    def node(self, **kwargs: dict[str, object]) -> Node:
        instance_id = kwargs.get("instance_id", None)
        _nodes = self.provisioner.list_nodes(ex_node_ids=[instance_id])
        if _nodes:
            return _nodes[0]
        raise ProvisionException("Unable to get node information")

    def __str__(self) -> str:
        return f"<AWSProvisioner [{self.options['region']}]>"


class GCEProvisioner(BaseProvisioner):
    """Provides abstraction for the GCE provisioner

    Required Environment Variables:

        - **GOOGLE_APPLICATION_SERVICE_ACCOUNT**
        - **GOOGLE_APPLICATION_CREDENTIALS**
        - **GOOGLE_PROJECT**
        - **GOOGLE_DATACENTER**

    """

    @property
    def options(self) -> t.Mapping[str, str]:
        return {
            "user_id": self.env.get("GOOGLE_APPLICATION_SERVICE_ACCOUNT", ""),
            "key": self.env.get("GOOGLE_APPLICATION_CREDENTIALS", ""),
            "project": self.env.get("GOOGLE_PROJECT", ""),
            "datacenter": self.env.get("GOOGLE_DATACENTER", ""),
        }

    # @retry(tries=5, logger=None)
    def connect(self) -> NodeDriver:
        gce = get_driver(Provider.GCE)
        log.debug(f"Establing provider connection...{gce} - {self.options}")
        return gce(**self.options)

    def destroy(self, nodes: list[MachineModel]) -> bool:
        _nodes = self.provisioner.ex_destroy_multiple_nodes(
            node_list=[node.state() for node in nodes], destroy_boot_disk=True
        )  # type: ignore
        return all([node is True for node in _nodes])

    def setup(self) -> None:
        tags = self.layout.tags or []
        if self.layout.ports:
            self.create_firewall(self.layout.name, self.layout.ports, tags)

    def cleanup(self, node: MachineModel, **kwargs: t.Mapping[str, t.Any]) -> bool:
        return True

    def image(self, runs_on: str) -> NodeImage:
        # Pull from partial first
        try:
            partial_image: NodeImage = self.provisioner.ex_get_image_from_family(runs_on)  # type: ignore
            if partial_image:
                return partial_image
        except ResourceNotFoundError:
            log.debug(f"Could not find {runs_on}, falling back internal image map")
        _runs_on = CLOUD_IMAGE_MAP["google"].get(runs_on)
        try:
            return [i for i in self.images() if i.name == _runs_on][0]
        except IndexError:
            raise ProvisionException(f"Could not determine image for {_runs_on}")

    def create_firewall(self, name: str, ports: list[str], tags: list[str]) -> None:
        ports = [port.split(":")[0] for port in ports]
        try:
            self.provisioner.ex_get_firewall(name)  # type: ignore
        except ResourceNotFoundError:
            log.warning("No firewall found, will create one to attach nodes to.")
            self.provisioner.ex_create_firewall(  # type: ignore
                name, [{"IPProtocol": "tcp", "ports": ports}], target_tags=tags
            )

    def delete_firewall(self, name: str) -> None:
        try:
            self.provisioner.ex_destroy_firewall(self.provisioner.ex_get_firewall(name))  # type: ignore
        except ResourceNotFoundError:
            log.error(f"Unable to delete firewall {name}")

    def list_firewalls(self) -> list[str]:
        return self.provisioner.ex_list_firewalls()  # type: ignore

    def create(self) -> list[MachineModel] | None:
        image = self.image(self.layout.runs_on)
        if not image and not self.layout.username:
            raise ProvisionException(
                f"Could not locate AMI and/or username for: {self.layout.runs_on}"
            )
        size = self.sizes(self.layout.instance_size)[0]
        ex_metadata = {
            "items": [
                {
                    "key": "ssh-keys",
                    "value": "%s: %s"
                    % (
                        self.layout.username,
                        Path(self.layout.ssh_public_key)
                        .expanduser()
                        .read_text()
                        .strip(),
                    ),
                },
                {
                    "key": "startup-script",
                    "value": self._userdata()
                    if "windows" not in self.layout.runs_on
                    else "",
                },
            ]
        }
        if "windows" in self.layout.runs_on:
            # Install ssh
            ex_metadata["items"].append(
                {
                    "key": "sysprep-specialize-script-cmd",
                    "value": "googet -noconfirm=true install google-compute-engine-ssh",
                }
            )
            ex_metadata["items"].append({"key": "enable-windows-ssh", "value": "TRUE"})

        if self.layout.ports:
            self.create_firewall(self.layout.name, self.layout.ports, self.layout.tags)

        now = datetime.datetime.utcnow().strftime("created-%Y-%m-%d")
        if self.layout.tags:
            self.layout.tags.append(now)
            self.layout.tags.append(f"user-{os.environ.get('USER', 'ogc')}")
            # Store some extra metadata similar to what other projects use
            self.layout.tags.append("environment-ogc")
            self.layout.tags.append("repo-ogc")

        suffix = str(uuid.uuid4())[:4]
        opts = dict(
            base_name=f"ogc-{self.layout.name}-{suffix}",
            image=image,
            size=size,
            number=self.layout.scale,
            ex_metadata=ex_metadata,
            ex_tags=self.layout.tags,
            ex_labels=self.layout.labels,
            ex_disk_type="pd-ssd",
            ex_disk_size=100,
            ex_preemptible=os.environ.get("OGC_ENABLE_SPOT", False),
        )
        _nodes = self.provisioner.ex_create_multiple_nodes(**opts)  # type: ignore
        _machines = []
        for node in _nodes:
            if not hasattr(node, "id"):
                raise ProvisionException(
                    f"Failed to create node {node.name}: ({node.code}) {node.error}"
                )
            state_file_p = db.cache_path() / node.id
            state_file_p.write_bytes(db.model_as_pickle(node))
            machine = MachineModel(
                layout=self.layout,
                instance_name=node.name,
                instance_id=node.id,
                instance_state=node.state,
                public_ip=node.public_ips[0],
                private_ip=node.private_ips[0],
                remote_state_file=(db.cache_path() / node.id).resolve(),
            )
            machine.save()
            _machines.append(machine)
        return _machines

    def node(self, **kwargs: dict[str, object]) -> Node | None:
        _nodes = self.provisioner.list_nodes()
        instance_id = None
        if "instance_id" in kwargs:
            instance_id = kwargs["instance_id"]
        _node = [n for n in _nodes if n.id == instance_id]
        return _node[0] if len(_node) > 0 else None

    def __str__(self) -> str:
        return f"<GCEProvisioner [{self.options['datacenter']}]>"


@signals.init.connect
def choose_provisioner(
    layout: LayoutModel,
) -> BaseProvisioner:
    choices = {"aws": AWSProvisioner, "google": GCEProvisioner}
    provisioner: t.Type[BaseProvisioner] = choices[str(layout.provider)]
    p = provisioner(layout=layout)
    p.connect()
    return p
