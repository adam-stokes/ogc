# pylint: disable=wrong-import-position
# pylint: disable=wrong-import-order

import re
import sys
import uuid
from pathlib import Path
from typing import List

from libcloud.compute.base import NodeAuthSSHKey
from libcloud.compute.deployment import MultiStepDeployment
from libcloud.compute.providers import get_driver
from libcloud.compute.ssh import ParamikoSSHClient
from libcloud.compute.types import Provider
from retry.api import retry_call
from scp import SCPClient

from ogc.cache import Cache
from ogc.enums import CLOUD_IMAGE_MAP
from ogc.exceptions import ProvisionException


class ProvisionResult:
    def __init__(self, id, node, layout, env):
        self.node = node
        self.layout = layout
        self.node = node[0]
        self.host = node[1][0]
        self.private_ips = self.node.private_ips[0]
        self.env = env
        self.id = id
        self.username = self.layout.username
        self.ssh_public_key = self.layout.ssh.public.resolve()
        self.ssh_private_key = self.layout.ssh.private.resolve()

    def save(self):
        cache_obj = Cache()
        cache_obj.save(self.layout.name, self)

    def reload(self):
        return ProvisionResult.load(self.layout.name)

    @classmethod
    def load(cls, name):
        cache_obj = Cache()
        cache_obj.load(name)


class ProvisionConstraint:
    """Parses the constraints to give us a proper node size for selected cloud"""

    def __init__(self, constraint):
        self.constraint = constraint

    def parse(self):
        items = self.constraint.split(" ")
        params = {}
        for item in items:
            prop, val = item.split("=")
            try:
                params[prop] = self.bytesto(self.parse_size(val), "m")
            except ValueError:
                params[prop] = val
        return params

    def bytesto(bytes, to, bsize=1024):
        a = {"k": 1, "m": 2, "g": 3, "t": 4, "p": 5, "e": 6}
        r = float(bytes)
        return int(bytes / (bsize ** a[to]))

    def parse_size(self, size):
        if isinstance(size, int):
            return size
        m = re.match(r"^(\d+(?:\.\d+)?)\s*([KMGT]?B)?$", size.upper())
        if m:
            number, unit = m.groups()
            return int(float(number) * self.units[unit])
        raise ValueError("Invalid size")


class BaseProvisioner:
    def __init__(self, env, **kwargs):
        self._args = kwargs
        self.env = env
        self.uuid = f"ogc-{str(uuid.uuid4())[:8]}"
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

    def sizes(self, constraints):
        _sizes = self.provisioner.list_sizes()
        try:
            return [
                size
                for size in _sizes
                if size.id == constraints or size.name == constraints
            ][0]
        except IndexError:
            raise ProvisionException(
                f"Could not locate instance size for {constraints}"
            )

    def image(self, runs_on, arch):
        """Gets a single image from registry of provider"""
        return self.provisioner.get_image(runs_on)

    def images(self, **kwargs):
        return self.provisioner.list_images(**kwargs)

    def _create_node(self, **kwargs) -> ProvisionResult:
        _opts = kwargs.copy()
        layout = None
        if "ogc_layout" in _opts:
            layout = _opts["ogc_layout"]
            del _opts["ogc_layout"]

        env = None
        if "ogc_env" in _opts:
            env = _opts["ogc_env"]
            del _opts["ogc_env"]

        node = self.provisioner.create_node(**_opts)
        node = self.provisioner.wait_until_running(
            nodes=[node], wait_period=5, timeout=300
        )[0]
        result = ProvisionResult(self.uuid, node, layout, env)
        result.save()
        return result

    def node(self, **kwargs):
        return self.provisioner.list_nodes(**kwargs)

    def create_keypair(self, ssh):
        return self.provisioner.import_key_pair_from_file(
            name=self.uuid, key_file_path=str(ssh.public)
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

    def setup(self, layout):
        self.create_keypair(layout.ssh)

    def cleanup(self, node):
        key_pair = self.get_key_pair(node.id)
        return self.delete_key_pair(key_pair)

    def image(self, runs_on, arch):
        if runs_on.startswith("ami-"):
            _runs_on = runs_on
        else:
            # FIXME: need proper architecture detection
            _runs_on = CLOUD_IMAGE_MAP["aws"][arch].get(runs_on)
        return super().image(_runs_on, arch)

    def create(self, layout, env, **kwargs) -> ProvisionResult:
        auth = NodeAuthSSHKey(layout.ssh.public.read_text())
        image = self.image(layout.runs_on, layout.arch)
        if not image and not layout.username:
            raise ProvisionException(
                f"Could not locate AMI and/or username for: {layout.runs_on}/{layout.arch}"
            )
        size = self.sizes(layout.constraints)

        opts = dict(
            name=f"ogc-{layout.name}",
            image=image,
            size=size,
            auth=auth,
            ex_securitygroup="e2e",
            ex_spot=True,
            ex_terminate_on_shutdown=True,
            ogc_layout=layout,
            ogc_env=env,
        )
        return self._create_node(**opts)

    def node(self, **kwargs):
        instance_id = None
        if "instance_id" in kwargs:
            instance_id = kwargs["instance_id"]
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
        pass

    def image(self, runs_on, arch):
        _runs_on = CLOUD_IMAGE_MAP["google"][arch].get(runs_on)
        try:
            return [i for i in self.images() if i.name == _runs_on][0]
        except IndexError:
            raise ProvisionException(f"Could not determine image for {_runs_on}")

    def create(self, layout, env, **kwargs) -> ProvisionResult:
        image = self.image(layout.runs_on, layout.arch)
        if not image and not layout.username:
            raise ProvisionException(
                f"Could not locate AMI and/or username for: {layout.runs_on}/{layout.arch}"
            )
        size = self.sizes(layout.constraints)

        ex_metadata = {
            "items": [
                {
                    "key": "ssh-keys",
                    "value": "root: %s" % (layout.ssh.public.read_text()),
                }
            ]
        }

        opts = dict(
            name=f"ogc-{layout.name}",
            image=image,
            size=size,
            ex_metadata=ex_metadata,
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


class Deployer:
    def __init__(self, deployment: ProvisionResult):
        self.deployment = deployment
        self.layout = self.deployment.layout
        self.env = self.deployment.env

        engine = choose_provisioner(self.layout.provider, env=self.env)
        self.node = engine.node(instance_id=self.deployment.node.id)
        self._ssh_client = ParamikoSSHClient(
            self.deployment.host,
            username=self.deployment.username,
            key=str(self.deployment.ssh_private_key),
            timeout=300,
        )
        retry_call(self._ssh_client.connect, tries=15, delay=5)

    def _progress(self, filename, size, sent, peername):
        if isinstance(filename, bytes):
            filename = filename.decode("utf8")
        sys.stdout.write(
            "[%s:%s] %s progress: %.2f%%                           \r"
            % (self.layout.name, peername[0], filename, float(sent) / float(size) * 100)
        )
        sys.stdout.flush()

    def run(self, context, msg_cb):
        msg_cb(
            f"Establishing connection [{self.deployment.host}] [{self.deployment.username}] [{str(self.deployment.ssh_private_key)}]"
        )
        steps = [step.render(context) for step in self.layout.steps]
        if steps:
            msg_cb(f"Executing deployment actions for {self.layout.name}")
            msd = MultiStepDeployment(steps)
            msd.run(self.node, self._ssh_client)
            return DeployerResult(self.deployment, msd)
        msg_cb("No deployment actions listed, skipping.")
        return None

    def put(self, src: Path, dst: Path, excludes: List[str], msg_cb):
        scp = SCPClient(self._ssh_client._get_transport(), progress4=self._progress)
        if src.is_dir():
            msg_cb(f"Uploading directory contents of [{src}] to [{dst}]")
            scp.put(str(src), remote_path=str(dst), recursive=True)
        else:
            msg_cb(f"Uploading file [{src}] to [{dst}]")
            scp.put(str(src), str(dst))
        scp.close()
        sys.stdout.write("\n")

    def get(self, dst: Path, src: Path, msg_cb):
        scp = SCPClient(self._ssh_client._get_transport(), progress4=self._progress)
        if str(src).endswith("/"):
            msg_cb(f"Downloading destination contents of [{dst}] to [{src}]")
            scp.get(remote_path=str(dst), local_path=str(src), recursive=True)
        else:
            msg_cb(f"Downloading file [{dst}] to [{src}]")
            scp.get(remote_path=str(dst), local_path=str(src))
        scp.close()
        sys.stdout.write("\n")


class DeployerResult:
    def __init__(self, deployment: Deployer, msd: MultiStepDeployment):
        self.deployment = deployment
        self.msd = msd

    def show(self, msg_cb):
        msg_cb("Deployment Result: ")
        for step in self.msd.steps:
            msg_cb(f"  - [{step.exit_status}]: {step}")
        msg_cb("Connection Information: ")
        msg_cb(
            f"  - Node: {self.deployment.layout.name} [{self.deployment.node.state}]"
        )
        msg_cb(
            f"  - ssh -i {self.deployment.ssh_private_key} {self.deployment.username}@{self.deployment.host}"
        )
        msg_cb("")
