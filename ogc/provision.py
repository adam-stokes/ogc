from libcloud.compute.base import NodeAuthSSHKey
from libcloud.compute.deployment import MultiStepDeployment
from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider


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
        return self.provisioner.list_images()

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
            image for image in self.provisioner.list_images() if "ami-" in image.id
        ]
        return ami_images

    def deploy(self, layout, ssh, **kwargs):
        _ssh = NodeAuthSSHKey(ssh.public.read_text())
        msd = MultiStepDeployment([step.render() for step in layout.steps])
        image = self.image("ami-0d90bed76900e679a")
        sizes = self.sizes()
        size = [size for size in sizes if size.id == "c5.4xlarge"]
        opts = dict(
            name="test-adam",
            image=image,
            size=size[0],
            ssh_key=ssh.private,
            ssh_username="admin",
            deploy=msd,
            auth=_ssh,
            ex_securitygroup="e2e",
        )
        return (super().deploy(**opts), msd)

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
