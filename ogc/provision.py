# pylint: disable=wrong-import-position
# pylint: disable=wrong-import-order

import re
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List

from libcloud.compute.base import NodeAuthSSHKey
from libcloud.compute.deployment import (
    FileDeployment,
    MultiStepDeployment,
    ScriptDeployment,
)
from libcloud.compute.providers import get_driver
from libcloud.compute.ssh import ParamikoSSHClient
from libcloud.compute.types import Provider
from mako.lookup import TemplateLookup
from mako.template import Template
from retry.api import retry_call
from scp import SCPClient

from ogc import log
from ogc.db import NodeModel
from ogc.enums import CLOUD_IMAGE_MAP
from ogc.exceptions import ProvisionException


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

    def save(self) -> NodeModel:
        node_obj = NodeModel(
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
        )
        node_obj.save()
        return node_obj


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

    def _create_node(self, **kwargs) -> NodeModel:
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
        node = self.provisioner.create_node(**_opts)
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
        key_pair = self.get_key_pair(node.uuid)
        return self.delete_key_pair(key_pair)

    def image(self, runs_on, arch):
        if runs_on.startswith("ami-"):
            _runs_on = runs_on
        else:
            # FIXME: need proper architecture detection
            _runs_on = CLOUD_IMAGE_MAP["aws"][arch].get(runs_on)
        return super().image(_runs_on, arch)

    def create(self, layout, env, **kwargs) -> NodeModel:
        pub_key = Path(layout["ssh_public_key"]).read_text()
        auth = NodeAuthSSHKey(pub_key)
        image = self.image(layout["runs_on"], layout["arch"])
        if not image and not layout["username"]:
            raise ProvisionException(
                f"Could not locate AMI and/or username for: {layout['runs_on']}/{layout['arch']}"
            )
        size = self.sizes(layout["constraints"])

        opts = dict(
            name=f"ogc-{layout['name']}",
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

    def create(self, layout, env, **kwargs) -> NodeModel:
        image = self.image(layout["runs_on"], layout["arch"])
        if not image and not layout["username"]:
            raise ProvisionException(
                f"Could not locate AMI and/or username for: {layout['runs_on']}/{layout['arch']}"
            )
        size = self.sizes(layout["constraints"])

        ex_metadata = {
            "items": [
                {
                    "key": "ssh-keys",
                    "value": "root: %s" % (Path(layout["ssh_public_key"]).read_text()),
                }
            ]
        }

        opts = dict(
            name=f"ogc-{self.uuid}-{layout['name']}",
            image=image,
            size=size,
            ex_metadata=ex_metadata,
            ex_tags=["e2e"],
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
    def __init__(self, deployment: NodeModel, env: Dict[str, str]):
        self.deployment = deployment
        self.env = env

        engine = choose_provisioner(self.deployment.provider, env=self.env)
        self.node = engine.node(instance_id=self.deployment.instance_id)
        self._ssh_client = ParamikoSSHClient(
            self.deployment.public_ip,
            username=self.deployment.username,
            key=str(self.deployment.ssh_private_key),
            timeout=300,
        )
        retry_call(self._ssh_client.connect, tries=20, delay=15, backoff=2)

    def render(self, template: Path, context):
        """Returns the correct deployment based on type of step"""
        fpath = template.absolute()
        lookup = TemplateLookup(
            directories=[
                str(template.parent.absolute()),
                str(template.parent.parent.absolute()),
            ]
        )
        template = Template(filename=str(fpath), lookup=lookup)
        return template.render(**context)

    def exec(self, cmd) -> "DeployerResult":
        """Runs a command on the node"""
        script = ScriptDeployment(cmd)
        msd = MultiStepDeployment([script])
        msd.run(self.node, self._ssh_client)
        return DeployerResult(self.deployment, msd)

    def run(self) -> "DeployerResult":
        log.info(
            f"Establishing connection [{self.deployment.public_ip}] [{self.deployment.username}] [{str(self.deployment.ssh_private_key)}]"
        )
        scripts = Path(self.deployment.scripts)
        if not scripts.exists():
            log.info("No deployment scripts found, skipping.")
            return DeployerResult(self.deployment, MultiStepDeployment())

        # TODO: maybe support a "vars" section in the spec file to be
        # added to the context for templates
        context = {"env": self.env}

        # teardown file is a special file that gets executed before node
        # destroy
        scripts_to_run = [
            fname for fname in scripts.glob("**/*") if fname.stem != "teardown"
        ]
        scripts_to_run.reverse()

        steps = [
            ScriptDeployment(self.render(s, context))
            for s in scripts_to_run
            if s.is_file()
        ]

        # Add teardown script as just a filedeployment
        teardown_script = scripts / "teardown"
        if teardown_script.exists():
            with tempfile.NamedTemporaryFile(delete=False) as fp:
                temp_contents = self.render(teardown_script, context)
                fp.write(temp_contents.encode())
                steps.append(FileDeployment(fp.name, "teardown"))
                steps.append(ScriptDeployment("chmod +x teardown"))

        if steps:
            log.info(f"[{self.deployment.instance_name}] Executing {len(steps)} steps")
            msd = MultiStepDeployment(steps)
            msd.run(self.node, self._ssh_client)
            return DeployerResult(self.deployment, msd)
        return DeployerResult(self.deployment, MultiStepDeployment())

    def _progress(self, filename, size, sent, peername):
        if isinstance(filename, bytes):
            filename = filename.decode("utf8")
        sys.stdout.write(
            "[%s:%s] %s progress: %.2f%%                           \r"
            % (
                self.deployment.instance_name,
                peername[0],
                filename,
                float(sent) / float(size) * 100,
            )
        )
        sys.stdout.flush()

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
    def __init__(self, deployment: NodeModel, msd: MultiStepDeployment):
        self.deployment = deployment
        self.msd = msd

    @property
    def passed(self):
        return all(
            step.exit_status == 0
            for step in self.msd.steps
            if hasattr(step, "exit_status")
        )

    def show(self):
        log.info("Deployment Result: ")
        for step in self.msd.steps:
            if hasattr(step, "exit_status"):
                log.info(f"  - [{step.exit_status}]: {step}")
        log.info("Connection Information: ")
        log.info(
            f"  - Node: {self.deployment.instance_name} [{self.deployment.instance_state}]"
        )
        log.info(
            f"  - ssh -i {self.deployment.ssh_private_key} {self.deployment.username}@{self.deployment.public_ip}"
        )
