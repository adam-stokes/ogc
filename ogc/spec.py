import json
import signal
import sys
from pathlib import Path

import yaml
from melddict import MeldDict
from slugify import slugify

from ogc import db
from ogc.exceptions import SpecLoaderException

from .state import app


class SpecProvisionLayout:
    def __init__(self, layout, env, ssh):
        self.name, self.layout = layout
        self.env = env
        self.ssh = ssh
        self._scale = self.layout.get("scale", 1)

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
        return self._scale

    @scale.setter
    def scale(self, val):
        self._scale = val

    @property
    def tags(self):
        _tags = self.layout.get("tags", [])
        return [slugify(tag) for tag in _tags if tag]

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

    @property
    def ports(self):
        return self.layout.get("ports", [])

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
            "ports": self.ports,
        }

    def as_json(self):
        return json.dumps(self.as_dict())


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
        with app.session as session:
            counts = {
                layout.name: {"scale": layout.scale, "deployed": 0, "remaining": 0}
                for layout in self.layouts
            }
            for layout in self.layouts:
                deployed_count = (
                    session.query(db.Node)
                    .filter(db.Node.instance_name.endswith(layout.name))
                    .count()
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

    @property
    def is_deployed(self):
        """Returns whether there are any deployments at all"""
        return any(stat["deployed"] > 0 for stat in self.status.values())

    @property
    def deploy_status(self):
        status_text = "[bold green]Healthy[/]"
        if self.is_degraded and self.is_deployed:
            status_text = "[bold red]Degraded[/]"
        elif not self.is_deployed:
            status_text = "Idle"
        return status_text

    def get_layout(self, name):
        """Returns a layout for a given name/key"""
        return [layout for layout in self.layouts if layout.name == name]

    def __repr__(self):
        return f"<SpecProvisionPlan [{self.name}] {self.layouts}>"

    def _sighandler(self, sig, frame):
        self.force_shutdown = True
        app.log.debug(f"Caught signal {sig} - {frame}")
        sys.exit(1)


class SpecLoader(MeldDict):
    @classmethod
    def load(cls, specs: list[str]) -> "SpecProvisionPlan":
        if Path("ogc.yml").exists():
            specs.insert(0, "ogc.yml")

        _specs = []
        for sp in specs:
            _path = Path(sp)
            if not _path.exists():
                raise SpecLoaderException(f"Could not find {_path}")
            _specs.append(_path)

        if not _specs:
            raise SpecLoaderException(
                f"No provision specs found, please specify with `--spec <file.yml>`"
            )

        cl = SpecLoader()
        for spec in _specs:
            cl += yaml.load(spec.read_text(), Loader=yaml.FullLoader)
        return SpecProvisionPlan(cl)
