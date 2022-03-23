# pylint: disable=wrong-import-position
# pylint: disable=wrong-import-order


import tempfile
from pathlib import Path
from typing import Dict, List

import sh
from libcloud.compute.deployment import (
    FileDeployment,
    MultiStepDeployment,
    ScriptDeployment,
)
from libcloud.compute.ssh import ParamikoSSHClient
from mako.lookup import TemplateLookup
from mako.template import Template
from retry.api import retry_call

from ogc import log
from ogc.db import NodeActionResult, NodeModel
from ogc.provision import choose_provisioner


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
        retry_call(self._ssh_client.connect, tries=10, delay=5, backoff=2)

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

    def put(self, src: str, dst: str, excludes: List[str]):
        cmd_opts = [
            "-avz",
            "-e",
            f"'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i {self.deployment.ssh_private_key}'",
            src,
            f"{self.deployment.username}@{self.deployment.public_ip}:{dst}",
        ]
        if excludes:
            for exclude in excludes:
                cmd_opts.append(f"--exclude='{exclude}'")
        sh.rsync(cmd_opts)

    def get(self, dst: str, src: str):
        cmd_opts = [
            "-avz",
            "-e",
            f"'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i {self.deployment.ssh_private_key}'",
            f"{self.deployment.username}@{self.deployment.public_ip}:{dst}",
            src,
        ]
        sh.rsync(cmd_opts)


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
                NodeActionResult.create(
                    node=self.deployment,
                    exit_code=step.exit_status,
                    out=step.stdout,
                    err=step.stderr,
                )
                log.info(f"  - [{step.exit_status}]: {step}")
        log.info("Connection Information: ")
        log.info(
            f"  - Node: {self.deployment.instance_name} [{self.deployment.instance_state}]"
        )
        log.info(
            f"  - ssh -i {self.deployment.ssh_private_key} {self.deployment.username}@{self.deployment.public_ip}"
        )