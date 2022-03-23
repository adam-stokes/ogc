import signal
import sys
from pathlib import Path

import yaml
from melddict import MeldDict

from ogc import db

from .state import app


class SpecLoader(MeldDict):
    @classmethod
    def load(cls, specs):
        cl = SpecLoader()
        for spec in specs:
            cl += yaml.load(spec.read_text(), Loader=yaml.FullLoader)
        return SpecProvisionPlan(cl)


class SpecProvisionLayout:
    def __init__(self, layout, env, ssh):
        self.name, self.layout = layout
        self.env = env
        self.ssh = ssh

    def __repr__(self):
        return f"<SpecProvisionLayout [{self.name}]>"

    @property
    def runs_on(self):
        return self.layout.get("runs-on", "ubuntu-latest")

    @property
    def arch(self):
        return self.layout.get("arch", "amd64")

    @property
    def instance_size(self):
        return self.layout.get("instance_size", "e2-standard-8")

    @property
    def username(self):
        return self.layout.get("username", "admin")

    @property
    def scripts(self):
        return self.layout.get("scripts", "scripts")

    @property
    def provider(self):
        return self.layout.get("provider", "google")

    @property
    def scale(self):
        return self.layout.get("scale", 1)

    @property
    def tags(self):
        return self.layout.get("tags", [])

    @property
    def artifacts(self):
        return self.layout.get("artifacts", None)

    @property
    def remote_path(self):
        return self.layout.get("remote-path", None)

    @property
    def include(self):
        return self.layout.get("include", [])

    @property
    def exclude(self):
        return self.layout.get("exclude", [])

    def as_dict(self):
        return {
            "name": self.name,
            "runs-on": self.runs_on,
            "scale": self.scale,
            "arch": self.arch,
            "instance-size": self.instance_size,
            "username": self.username,
            "scripts": self.scripts,
            "provider": self.provider,
            "ssh_public_key": str(self.ssh.public),
            "ssh_private_key": str(self.ssh.private),
            "tags": self.tags,
            "artifacts": self.artifacts,
            "remote-path": self.remote_path,
            "include": self.include,
            "exclude": self.exclude,
        }


class SpecProvisionSSHKey:
    def __init__(self, sshkeys):
        self.sshkeys = sshkeys

    @property
    def public(self) -> Path:
        return Path(self.sshkeys.get("public")).expanduser()

    @property
    def private(self) -> Path:
        return Path(self.sshkeys.get("private")).expanduser()


class SpecProvisionPlan:
    """A Provision Plan specification"""

    def __init__(self, plan):
        self.plan = plan
        self.force_shutdown = False
        for sig in [1, 2, 3, 5, 6, 15]:
            signal.signal(sig, self._sighandler)

    @property
    def layouts(self):
        return [
            SpecProvisionLayout(layout=layout, env=app.env, ssh=self.ssh)
            for layout in self.plan["layouts"].items()
        ]

    @property
    def name(self):
        return self.plan.get("name")

    @property
    def providers(self):
        return self.plan.get("providers", {})

    @property
    def ssh(self):
        return SpecProvisionSSHKey(self.plan.get("ssh-keys", {}))

    @property
    def status(self):
        """Return the status of the plan based on whats deployed and whats remaining"""
        db.connect()
        counts = {
            layout.name: {"scale": layout.scale, "deployed": 0, "remaining": 0}
            for layout in self.layouts
        }
        for layout in self.layouts:
            deployed_count = len(
                db.NodeModel.select().where(
                    db.NodeModel.instance_name.endswith(layout.name)
                )
            )
            remaining_count = layout.scale - deployed_count
            action = "add" if remaining_count >= 0 else "remove"
            counts[layout.name]["deployed"] = deployed_count
            counts[layout.name]["remaining"] = remaining_count
            counts[layout.name]["action"] = action
        return counts

    @property
    def is_degraded(self):
        """Returns whether there are missing deployments"""
        return any(
            stat["remaining"] > 0 or stat["remaining"] < 0
            for stat in self.status.values()
        )

    def get_layout(self, name):
        """Returns a layout for a given name/key"""
        return [layout for layout in self.layouts if layout.name == name]

    def __repr__(self):
        return f"<SpecProvisionPlan [{self.name}] {self.layouts}>"

    def _sighandler(self, sig, frame):
        self.force_shutdown = True
        app.log.debug(f"Caught signal {sig} - {frame}")
        sys.exit(1)
