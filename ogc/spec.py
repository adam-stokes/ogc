import signal

import yaml
from libcloud.compute.deployment import MultiStepDeployment, ScriptDeployment
from melddict import MeldDict

from .state import app


class SpecLoader(MeldDict):
    @classmethod
    def load(cls, specs):
        cl = SpecLoader()
        for spec in specs:
            cl += yaml.load(spec.read_text(), Loader=yaml.FullLoader)
        return SpecProvisionPlan(cl)


class SpecProvisionLayout:
    def __init__(self, layout):
        self.name, self.layout = layout

    def __repr__(self):
        return f"<SpecProvisionLayout [{self.name}]>"

    @property
    def runs_on(self):
        return self.layout.get("runs-on", "ubuntu-latest")

    @property
    def username(self):
        return self.layout.get("username", "admin")

    @property
    def scripts(self):
        return self.layout.get("scripts", [])

    @property
    def arches(self):
        return self.layout.get("arches", ["amd64"])

    def provision(self, engine):
        step = ScriptDeployment("echo whoami ; date ; ls -la")
        msd = MultiStepDeployment([step])
        image = engine.provisioner.get_image("ami-0d90bed76900e679a")
        sizes = engine.sizes()
        size = [size for size in sizes if size.id == "c5.4xlarge"]
        app.log.info(f"Deploying node with [{image}] [{size[0]}]")
        return engine.provisioner.create_node(
            name="test-adam", image=image, size=size[0]
        )


class SpecProvisionPlan:
    """A Provision Plan specification"""

    def __init__(self, plan):
        self.plan = plan
        self.force_shutdown = False
        for sig in [1, 2, 3, 5, 6, 15]:
            signal.signal(sig, self._sighandler)

    @property
    def layouts(self):
        return [SpecProvisionLayout(layout) for layout in self.plan["layouts"].items()]

    @property
    def name(self):
        return self.plan.get("name")

    @property
    def providers(self):
        return self.plan.get("providers", {})

    def get_layout(self, name):
        """Returns a layout for a given name/key"""
        return [layout for layout in self.layouts if layout.name == name]

    def __repr__(self):
        return f"<SpecProvisionPlan [{self.name}] {self.layouts}>"

    def _sighandler(self, sig, frame):
        self.force_shutdown = True
        app.log.debug(f"Caught signal {sig} - {frame}")
