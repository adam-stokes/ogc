# pylint: disable=wrong-import-position
# pylint: disable=wrong-import-order

import datetime
import json
import uuid
from pathlib import Path
from typing import Optional

from libcloud.common.google import ResourceNotFoundError
from libcloud.compute.base import NodeAuthSSHKey
from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider
from retry.api import retry_call

from ogc import db
from ogc.enums import CLOUD_IMAGE_MAP
from ogc.exceptions import ProvisionException
from ogc.log import Logger as log
from ogc.state import app


class ProvisionResult:
    def __init__(self, node, layout, env):
        self.node = node
        self.layout = layout
        self.node = node[0]
        self.public_ip = node[1][0]
        self.private_ip = self.node.private_ips[0]
        self.env = env
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
        with app.session as session:
            user = session.query(db.User).first()
            node_obj = db.Node(
                instance_name=self.node.name,
                instance_id=self.node.id,
                instance_state=self.node.state,
                username=self.username,
                public_ip=self.public_ip,
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
                layout=json.dumps(self.layout),
                extra=json.dumps({"env": self.env}),
                user=user,
            )
            session.add(node_obj)
            session.commit()
            return node_obj


class BaseProvisioner:
    def __init__(self, env, **kwargs):
        self._args = kwargs
        self.env = env
        self.provisioner = self.connect()

    @property
    def options(self):
        raise NotImplementedError()

    def connect(self):
        raise NotImplementedError()

    def create(self, layout, env, **kwargs):
        raise NotImplementedError()

    def setup(self, layout, **kwargs):
        """Perform some provider specific setup before launch"""
        raise NotImplementedError()

    def cleanup(self, node, **kwargs):
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

    def image(self, runs_on: str, arch: Optional[str] = None):
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

        log.info(f"Spinning up {layout['name']}")
        node = retry_call(
            self.provisioner.create_node, fkwargs=_opts, backoff=3, tries=5
        )
        node = self.provisioner.wait_until_running(
            nodes=[node], wait_period=5, timeout=300
        )[0]
        result = ProvisionResult(node, layout, env)
        node_obj = result.save()
        return node_obj

    def node(self, **kwargs):
        return self.provisioner.list_nodes(**kwargs)

    def create_keypair(self, name, ssh_public_key):
        return self.provisioner.import_key_pair_from_file(
            name=name, key_file_path=ssh_public_key
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

    def _userdata(self):
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

    def setup(self, layout, **kwargs):
        if layout["ports"]:
            self.create_firewall(layout["name"], layout["ports"])
        if not any(kp.name == layout["name"] for kp in self.list_key_pairs()):
            self.create_keypair(layout["name"], layout["ssh_public_key"])

    def cleanup(self, node, **kwargs):
        pass

    def image(self, runs_on, arch):
        if runs_on.startswith("ami-"):
            _runs_on = runs_on
        else:
            # FIXME: need proper architecture detection
            _runs_on = CLOUD_IMAGE_MAP["aws"][arch].get(runs_on)
        return super().image(_runs_on, arch)

    def create_firewall(self, name, ports):
        """Creates the security group for enabling traffic between nodes"""
        if not any(sg.name == name for sg in self.provisioner.ex_get_security_groups()):
            self.provisioner.ex_create_security_group(name, "ogc sg", vpc_id=None)

        for port in ports:
            ingress, egress = port.split(":")
            self.provisioner.ex_authorize_security_group(
                name, ingress, egress, "0.0.0.0/0", "tcp"
            )
            # udp
            # self.provisioner.ex_authorize_security_group(name, ingress, egress, "0.0.0.0/0", "udp")

    def delete_firewall(self, name):
        pass

    def create(self, layout, env, **kwargs) -> db.Node:
        pub_key = Path(layout["ssh_public_key"]).read_text()
        auth = NodeAuthSSHKey(pub_key)
        image = self.image(layout["runs-on"], layout["arch"])
        if not image and not layout["username"]:
            raise ProvisionException(
                f"Could not locate AMI and/or username for: {layout['runs-on']}/{layout['arch']}"
            )

        size = self.sizes(layout["instance-size"])

        opts = dict(
            name=f"ogc-{str(uuid.uuid4())[:8]}-{layout['name']}",
            image=image,
            size=size,
            auth=auth,
            ex_securitygroup=layout["name"],
            # ex_spot=True,
            ex_userdata=self._userdata() if 'windows' not in layout['runs-on'] else '',
            ex_terminate_on_shutdown=True,
            ogc_layout=layout,
            ogc_env=env,
        )
        tags = {}
        with app.session as session:
            user = session.query(db.User).first()
            # Store some metadata for helping with cleanup
            now = datetime.datetime.utcnow().strftime("created-%Y-%m-%d")
            layout["tags"].append(now)
            layout["tags"].append(f"user-{user.slug}")
            tags["Created"] = now
            tags["UserTag"] = f"user-{user.slug}"

        node = self._create_node(**opts)
        self.provisioner.ex_create_tags(self.node(instance_id=node.instance_id), tags)
        return node

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

    def setup(self, layout, **kwargs):
        self.create_firewall(layout["name"], layout["ports"], layout["tags"])

    def cleanup(self, node, **kwargs):
        pass

    def image(self, runs_on, arch):
        # Pull from partial first
        try:
            partial_image = self.provisioner.ex_get_image(runs_on)
            if partial_image:
                return partial_image
        except ResourceNotFoundError:
            log.debug(f"Could not find {runs_on}, falling back internal image map")
        _runs_on = CLOUD_IMAGE_MAP["google"][arch].get(runs_on)
        try:
            return [i for i in self.images() if i.name == _runs_on][0]
        except IndexError:
            raise ProvisionException(f"Could not determine image for {_runs_on}")

    def create_firewall(self, name, ports, tags):
        ports = [port.split(":")[0] for port in ports]
        try:
            self.provisioner.ex_get_firewall(name)
        except ResourceNotFoundError:
            log.warning("No firewall found, will create one to attach nodes to.")
            self.provisioner.ex_create_firewall(
                name, [{"IPProtocol": "tcp", "ports": ports}], target_tags=tags
            )

    def delete_firewall(self, name):
        try:
            self.provisioner.ex_destroy_firewall(self.provisioner.ex_get_firewall(name))
        except ResourceNotFoundError:
            log.error(f"Unable to delete firewall {name}")

    def list_firewalls(self):
        return self.provisioner.ex_list_firewalls()

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
                    "value": "%s: %s"
                    % (layout["username"], Path(layout["ssh_public_key"]).read_text()),
                },
                {
                    "key": "startup-script",
                    "value": self._userdata() if 'windows' not in layout['runs-on'] else '',
                },
            ]
        }

        if layout["ports"]:
            self.create_firewall(layout["name"], layout["ports"], layout["tags"])

        with app.session as session:
            user = session.query(db.User).first()
            # Store some metadata for helping with cleanup
            now = datetime.datetime.utcnow().strftime("created-%Y-%m-%d")
            layout["tags"].append(now)
            layout["tags"].append(f"user-{user.slug}")

        opts = dict(
            name=f"ogc-{str(uuid.uuid4())[:8]}-{layout['name']}",
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
