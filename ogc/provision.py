from gevent import monkey

monkey.patch_all()

from datetime import datetime

import click
from libcloud.compute.base import NodeAuthSSHKey
from libcloud.compute.deployment import MultiStepDeployment
from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider

from ogc.exceptions import ProvisionException


class ProvisionResult:
    def __init__(self, deploy, deploy_steps_results, layout, ssh):
        self.deploy = deploy
        self.layout = layout
        self.steps = deploy_steps_results.steps
        self.username = layout.username
        self.ssh = ssh

    def render(self, msg_cb):
        msg_cb("Provision Result: ")
        for step in self.steps:
            msg_cb(f"  - [{step.exit_status}]: {step}")
        msg_cb("Connection Information: ")
        msg_cb(f"  - Node: {self.deploy.name} [{self.deploy.state}]")
        msg_cb(
            f"  - ssh -i {self.ssh.private} {self.username}@{self.deploy.public_ips[0]}"
        )
        msg_cb("")


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

    def sizes(self, constraints):
        _sizes = self.provisioner.list_sizes()

        explicit_constraints = any(x in constraints for x in ["cores", "disk", "mem"])
        if not explicit_constraints:
            return [size for size in _sizes if size.id == constraints]
        raise ProvisionException(f"Could not locate instance size for {constraints}")

    def image(self, id):
        """Gets a single image from registry of provider"""
        return self.provisioner.get_image(id)

    def images(self, **kwargs):
        return self.provisioner.list_images(**kwargs)

    def deploy(self, **kwargs):
        return self.provisioner.deploy_node(**kwargs)

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
            "region": self._args.get("region"),
        }

    def connect(self):
        aws = get_driver(Provider.EC2)
        return aws(**self.options)

    def images_query(self, runs_on):
        """Returns the AMI and username to login with"""
        if runs_on.startswith("ami-"):
            return self.image(runs_on)
        return None

    def deploy(self, layout, ssh, msg_cb, **kwargs):
        msg_cb(f"Launching {layout}")
        _ssh = NodeAuthSSHKey(ssh.public.read_text())
        msd = MultiStepDeployment([step.render() for step in layout.steps])

        image = self.images_query(layout.runs_on)
        if not image and not layout.username:
            raise ProvisionException(
                f"Could not locate AMI and/or username for: {layout.runs_on}"
            )
        size = self.sizes(layout.constraints)
        if size and len(size) > 0:
            size = size[0]

        opts = dict(
            name="test-adam",
            image=image,
            size=size,
            ssh_key=ssh.private,
            ssh_username=layout.username,
            deploy=msd,
            auth=_ssh,
            ex_securitygroup="e2e",
        )
        node = super().deploy(**opts)
        return ProvisionResult(node, msd, layout, ssh)

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
            "project": self._args.get("project"),
            "datacenter": self._args.get("datacenter"),
        }

    def connect(self):
        gce = get_driver(Provider.GCE)
        return gce(**self.options)

    def __repr__(self):
        return f"<GCEProvisioner [{self.options['datacenter']}]>"


def choose_provisioner(name, options, env):
    choices = {"aws": AWSProvisioner, "google": GCEProvisioner}
    provisioner = choices[name]
    return provisioner(env, **options)
