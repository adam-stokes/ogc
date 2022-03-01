from datetime import datetime

import click
from libcloud.compute.base import NodeAuthSSHKey
from libcloud.compute.deployment import MultiStepDeployment
from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider

from ogc.exceptions import ProvisionException

from .enums import AWS_AMI_OWNERS


class ProvisionResult:
    def __init__(self, deploy, steps, username, ssh):
        self.deploy = deploy
        self.steps = steps.steps
        self.username = username
        self.ssh = ssh

    def render(self):
        click.secho("---")
        click.secho("Provision Result: ")
        for step in self.steps:
            click.secho(f"  - [{step.exit_status}]: {step}")
        click.secho("Connection Information: ")
        click.secho(f"  - Node: {self.deploy.name} [{self.deploy.state}]")
        click.secho(
            f"  - ssh -i {self.ssh.private} {self.username}@{self.deploy.public_ips[0]}"
        )
        click.secho("---")


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

    def sizes(self, **kwargs):
        return self.provisioner.list_sizes()

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

    def images(self, **kwargs):
        ami_images = [
            image
            for image in self.provisioner.list_images(**kwargs)
            if "ami-" in image.id and image.extra["architecture"] in ["x86_64", "amd64"]
        ]
        ami_images.sort(key=lambda img: img.extra["creation_date"])
        return ami_images

    def images_query(self, runs_on):
        """Returns the AMI and username to login with"""
        if runs_on.startswith("ami-"):
            return (self.image(runs_on), "admin")

        image_property = None
        params = {}
        if "ubuntu" in runs_on:
            image_property = AWS_AMI_OWNERS.get("ubuntu")

        elif "centos" in runs_on:
            image_property = AWS_AMI_OWNERS.get("centos")

        elif "sles" in runs_on:
            image_property = AWS_AMI_OWNERS.get("sles")

        elif "debian" in runs_on:
            image_property = AWS_AMI_OWNERS.get("debian")
        else:
            return (None, None)

        params["ex_owner"] = image_property["owner_id"]
        if image_property["prefix"]:
            params["ex_filters"] = {"name": f"{image_property['prefix']}{runs_on}*"}
        else:
            params["ex_filters"] = {"name": f"{runs_on}*"}

        images = self.images(**params)
        if len(images) > 0:
            return (images[-1], image_property["username"])
        return (None, None)

    def deploy(self, layout, ssh, **kwargs):
        _ssh = NodeAuthSSHKey(ssh.public.read_text())
        msd = MultiStepDeployment([step.render() for step in layout.steps])

        image, username = self.images_query(layout.runs_on)
        if not image and not username:
            raise ProvisionException(f"Could not locate AMI for: {layout.runs_on}")
        sizes = self.sizes()
        size = [size for size in sizes if size.id == "c5.4xlarge"]
        opts = dict(
            name="test-adam",
            image=image,
            size=size[0],
            ssh_key=ssh.private,
            ssh_username=username,
            deploy=msd,
            auth=_ssh,
            ex_securitygroup="e2e",
        )
        node = super().deploy(**opts)
        return ProvisionResult(node, msd, username, ssh)

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
