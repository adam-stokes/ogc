import signal
import sys
from pathlib import Path

import yaml
from libcloud.compute.deployment import ScriptDeployment
from mako.template import Template
from melddict import MeldDict

from .state import app


class SpecLoader(MeldDict):
    @classmethod
    def load(cls, specs):
        cl = SpecLoader()
        for spec in specs:
            cl += yaml.load(spec.read_text(), Loader=yaml.FullLoader)
        return SpecProvisionPlan(cl)


class SpecProvisionLayoutStep:
    def __init__(self, step):
        self.step = step

    def render(self, metadata):
        """Returns the correct deployment based on type of step"""
        if "script" in self.step:
            fpath = Path(self.step["script"]).absolute()
            if fpath.exists():
                template = Template(filename=str(fpath))
                contents = template.render(**metadata)
                return ScriptDeployment(contents)
            return ScriptDeployment(
                f"echo \"{self.step['script']}\" >> missing_scripts"
            )
        return ScriptDeployment(self.step["run"])


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
    def constraints(self):
        return self.layout.get("constraints", "disk=100G mem=8G cores=16 arch=amd64")

    @property
    def username(self):
        return self.layout.get("username", "admin")

    @property
    def steps(self):
        _steps = self.layout.get("steps", [])
        _processed_steps = []
        if _steps:
            for _step in _steps:
                _processed_steps.append(SpecProvisionLayoutStep(_step))
        return _processed_steps

    @property
    def provider(self):
        return self.layout.get("provider", [])


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

    def get_layout(self, name):
        """Returns a layout for a given name/key"""
        return [layout for layout in self.layouts if layout.name == name]

    def __repr__(self):
        return f"<SpecProvisionPlan [{self.name}] {self.layouts}>"

    def _sighandler(self, sig, frame):
        self.force_shutdown = True
        app.log.debug(f"Caught signal {sig} - {frame}")
        sys.exit(1)
