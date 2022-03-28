# pylint: disable=wrong-import-position
# pylint: disable=wrong-import-order

import datetime
import uuid
from pathlib import Path

from libcloud.common.google import ResourceNotFoundError
from libcloud.compute.base import NodeAuthSSHKey
from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider
from retry.api import retry_call
from rich.console import Console

from ogc import db, log
from ogc.enums import CLOUD_IMAGE_MAP
from ogc.exceptions import ProvisionException

console = Console()

class ProvisionResult:
    def __init__(self, id, node, layout, env):
        self.node = node
        self.layout = layout
        self.node = node[0]
        self.host = node[1][0]
        self.private_ip = self.node.private_ips[0]
        self.env = env
        self.id = id
        self.username = self.layout["username"]
        self.scripts = self.layout["scripts"]
        self.provider = self.layout["provider"]
        self.ssh_public_key = self.layout["ssh_public_key"]
        self.ssh_private_key = self.layout["ssh_private_key"]
        self.tags = self.layout["tags"]
        self.remote_path = self.layout["remote-path"]
        self.artifacts = self.layout["artifacts"]
        self.include = self.layout["include"]
        self.exclude = self.layout["exclude"]
        self.ports = self.layout["ports"]

    def save(self) -> db.Node:
        session = db.connect()
        node_obj = db.Node(
            uuid=self.id,
            instance_name=self.node.name,
            instance_id=self.node.id,
            instance_state=self.node.state,
            username=self.username,
            public_ip=self.host,
            private_ip=self.private_ip,
            ssh_public_key=self.ssh_public_key,
            ssh_private_key=self.ssh_private_key,
            provider=self.provider,
            scripts=self.scripts,
            tags=self.tags,
            remote_path=self.remote_path,
            artifacts=self.artifacts,
            include=self.include,
            exclude=self.exclude,
            ports=self.ports,
            created=datetime.datetime.utcnow()
        )
        session.add(node_obj)
        session.commit()
        session.close()
        return node_obj


class BaseProvisioner:
    def __init__(self, env, **kwargs):
        self._args = kwargs
        self.env = env
        self.uuid = str(uuid.uuid4())[:8]
        self.provisioner = self.connect()

    @property
    def options(self):
        raise NotImplementedError()

    def connect(self):
        raise NotImplementedError()

    def create(self, layout, env, **kwargs):
        raise NotImplementedError()

    def setup(self):
        """Perform some provider specific setup before launch"""
        raise NotImplementedError()

    def cleanup(self, node):
        """Perform some provider specific cleanup after node destroy typically"""
        raise NotImplementedError()

    def destroy(self, node):
        return self.provisioner.destroy_node(node)

    def sizes(self, instance_size):
        _sizes = self.provisioner.list_sizes()
        try:
            return [
                size
                for size in _sizes
                if size.id == instance_size or size.name == instance_size
            ][0]
        except IndexError:
            raise ProvisionException(
                f"Could not locate instance size for {instance_size}"
            )

    def image(self, runs_on, arch):
        """Gets a single image from registry of provider"""
        return self.provisioner.get_image(runs_on)

    def images(self, **kwargs):
        return self.provisioner.list_images(**kwargs)

    def _create_node(self, **kwargs) -> db.Node:
        _opts = kwargs.copy()
        layout = None
        if "ogc_layout" in _opts:
            layout = _opts["ogc_layout"]
            del _opts["ogc_layout"]

        env = None
        if "ogc_env" in _opts:
            env = _opts["ogc_env"]
            del _opts["ogc_env"]

        console.log(f"Spinning up {layout['name']}")
        node = retry_call(
            self.provisioner.create_node, fkwargs=_opts, backoff=3, tries=5
        )
        node = self.provisioner.wait_until_running(
            nodes=[node], wait_period=5, timeout=300
        )[0]
        result = ProvisionResult(self.uuid, node, layout, env)
        node_obj = result.save()
        return node_obj

    def node(self, **kwargs):
        return self.provisioner.list_nodes(**kwargs)

    def create_keypair(self, ssh_public_key):
        return self.provisioner.import_key_pair_from_file(
            name=self.uuid, key_file_path=ssh_public_key
        )

    def get_key_pair(self, name):
        return self.provisioner.get_key_pair(name)

    def delete_key_pair(self, key_pair):
        retry_call(
            self.provisioner.delete_key_pair, fargs=[key_pair], backoff=3, tries=15
        )

    def list_key_pairs(self):
        return self.provisioner.list_key_pairs()

    def __repr__(self):
        raise NotImplementedError()


class AWSProvisioner(BaseProvisioner):
    """AWS Provisioner

    Environment variables required:
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY
    """

    @property
    def options(self):
        return {
            "key": self.env.get("AWS_ACCESS_KEY_ID", None),
            "secret": self.env.get("AWS_SECRET_ACCESS_KEY", None),
            "region": self.env.get("AWS_REGION", "us-east-2"),
        }

    def connect(self):
        aws = get_driver(Provider.EC2)
        return aws(**self.options)

    def setup(self, ssh_public_key):
        self.create_keypair(ssh_public_key)

    def cleanup(self, node):
        self._delete_firewall(f"ogc-{node.uuid}")
        key_pair = self.get_key_pair(node.uuid)
        return self.delete_key_pair(key_pair)

    def image(self, runs_on, arch):
        if runs_on.startswith("ami-"):
            _runs_on = runs_on
        else:
            # FIXME: need proper architecture detection
            _runs_on = CLOUD_IMAGE_MAP["aws"][arch].get(runs_on)
        return super().image(_runs_on, arch)

    def _create_firewall(self, name, ports):
        """Creates the security group for enabling traffic between nodes"""
        self.provisioner.ex_create_security_group(name, "ogc sg", vpc_id=None)

        for port in ports:
            ingress, egress = port.split(":")
            self.provisioner.ex_authorize_security_group(
                name, ingress, egress, "0.0.0.0/0", "tcp"
            )
            # udp
            # self.provisioner.ex_authorize_security_group(name, ingress, egress, "0.0.0.0/0", "udp")

    def _delete_firewall(self, name):
        return self.provisioner.ex_delete_security_group(name)

    def create(self, layout, env, **kwargs) -> db.Node:
        pub_key = Path(layout["ssh_public_key"]).read_text()
        auth = NodeAuthSSHKey(pub_key)
        image = self.image(layout["runs-on"], layout["arch"])
        if not image and not layout["username"]:
            raise ProvisionException(
                f"Could not locate AMI and/or username for: {layout['runs-on']}/{layout['arch']}"
            )
        size = self.sizes(layout["instance-size"])

        if layout["ports"]:
            self._create_firewall(f"ogc-{self.uuid}", layout["ports"])

        opts = dict(
            name=f"ogc-{self.uuid}-{layout['name']}",
            image=image,
            size=size,
            auth=auth,
            ex_securitygroup=f"ogc-{self.uuid}",
            ex_spot=True,
            ex_terminate_on_shutdown=True,
            ogc_layout=layout,
            ogc_env=env,
        )
        return self._create_node(**opts)

    def node(self, **kwargs):
        instance_id = kwargs.get("instance_id", None)
        _nodes = super().node(ex_node_ids=[instance_id])
        if _nodes:
            return _nodes[0]
        raise ProvisionException("Unable to get node information")

    def __repr__(self):
        return f"<AWSProvisioner [{self.options['region']}]>"


class GCEProvisioner(BaseProvisioner):
    """Provides abstraction for the GCE provisioner

    Environment variables required:
    GOOGLE_APPLICATION_SERVICE_ACCOUNT: Service user_id associated with credentials
    GOOGLE_APPLICATION_CREDENTIALS: Credentials file for the service account
    """

    @property
    def options(self):
        return {
            "user_id": self.env.get("GOOGLE_APPLICATION_SERVICE_ACCOUNT", None),
            "key": self.env.get("GOOGLE_APPLICATION_CREDENTIALS", None),
            "project": self.env.get("GOOGLE_PROJECT", None),
            "datacenter": self.env.get("GOOGLE_DATACENTER", None),
        }

    def connect(self):
        gce = get_driver(Provider.GCE)
        return gce(**self.options)

    def setup(self, layout):
        pass

    def cleanup(self, node):
        self._delete_firewall(f"ogc-{node.uuid}")

    def image(self, runs_on, arch):
        _runs_on = CLOUD_IMAGE_MAP["google"][arch].get(runs_on)
        try:
            return [i for i in self.images() if i.name == _runs_on][0]
        except IndexError:
            raise ProvisionException(f"Could not determine image for {_runs_on}")

    def _create_firewall(self, name, ports, tags):
        ports = [port.split(":")[0] for port in ports]
        self.provisioner.ex_create_firewall(
            name, [{"IPProtocol": "tcp", "ports": ports}], target_tags=tags
        )

    def _delete_firewall(self, name):
        try:
            self.provisioner.ex_destroy_firewall(self.provisioner.ex_get_firewall(name))
        except ResourceNotFoundError:
            log.error(f"Unable to delete firewall {name}")

    def create(self, layout, env, **kwargs) -> db.Node:
        image = self.image(layout["runs-on"], layout["arch"])
        if not image and not layout["username"]:
            raise ProvisionException(
                f"Could not locate AMI and/or username for: {layout['runs-on']}/{layout['arch']}"
            )
        size = self.sizes(layout["instance-size"])

        ex_metadata = {
            "items": [
                {
                    "key": "ssh-keys",
                    "value": "root: %s" % (Path(layout["ssh_public_key"]).read_text()),
                }
            ]
        }

        if layout["ports"]:
            self._create_firewall(f"ogc-{self.uuid}", layout["ports"], layout["tags"])

        opts = dict(
            name=f"ogc-{self.uuid}-{layout['name']}",
            image=image,
            size=size,
            ex_metadata=ex_metadata,
            ex_tags=layout["tags"],
            ogc_layout=layout,
            ogc_env=env,
        )
        return self._create_node(**opts)

    def node(self, **kwargs):
        _nodes = super().node()
        instance_id = None
        if "instance_id" in kwargs:
            instance_id = kwargs["instance_id"]
        _node = [n for n in _nodes if n.id == instance_id]
        if _node:
            return _node[0]
        raise ProvisionException("Unable to get node information")

    def __repr__(self):
        return f"<GCEProvisioner [{self.options['datacenter']}]>"


def choose_provisioner(name, env, **kwargs):
    choices = {"aws": AWSProvisioner, "google": GCEProvisioner}
    provisioner = choices[name]
    return provisioner(env, **kwargs)
