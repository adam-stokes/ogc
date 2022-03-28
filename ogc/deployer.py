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

from ogc import db, log
from ogc.provision import choose_provisioner


class Deployer:
    def __init__(self, deployment: db.Node, env: Dict[str, str], force: bool = False):
        self.deployment = deployment
        self.env = env
        self.force = force

        engine = choose_provisioner(self.deployment.provider, env=self.env)
        self.node = engine.node(instance_id=self.deployment.instance_id)
        self._ssh_client = ParamikoSSHClient(
            self.deployment.public_ip,
            username=self.deployment.username,
            key=str(self.deployment.ssh_private_key),
            timeout=300,
        )
        tries = 10
        if self.force:
            tries = 1
        retry_call(self._ssh_client.connect, tries=tries, delay=5, backoff=1)

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

    def exec_scripts(self, script_dir) -> "DeployerResult":
        scripts = Path(script_dir)
        if not scripts.exists():
            log.info("No deployment scripts found, skipping.")
            return DeployerResult(self.deployment, MultiStepDeployment())

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

    def run(self) -> "DeployerResult":
        log.info(
            f"Establishing connection [{self.deployment.public_ip}] [{self.deployment.username}] [{str(self.deployment.ssh_private_key)}]"
        )

        # Upload any files first
        if self.deployment.remote_path:
            log.info(
                f"Uploading file/directory contents to {self.deployment.instance_name}"
            )
            self.put(
                ".",
                self.deployment.remote_path,
                self.deployment.exclude,
                self.deployment.include,
            )

        return self.exec_scripts(self.deployment.scripts)

    def put(self, src: str, dst: str, excludes: List[str], includes: List[str] = []):
        cmd_opts = [
            "-avz",
            "-e",
            f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i {self.deployment.ssh_private_key}",
            src,
            f"{self.deployment.username}@{self.deployment.public_ip}:{dst}",
        ]

        if includes:
            for include in includes:
                cmd_opts.append(f"--include={include}")

        if excludes:
            for exclude in excludes:
                cmd_opts.append(f"--exclude={exclude}")
        sh.rsync(cmd_opts)

    def get(self, dst: str, src: str):
        cmd_opts = [
            "-avz",
            "-e",
            f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i {self.deployment.ssh_private_key}",
            f"{self.deployment.username}@{self.deployment.public_ip}:{dst}",
            src,
        ]
        sh.rsync(cmd_opts)


class DeployerResult:
    def __init__(self, deployment: db.Node, msd: MultiStepDeployment):
        self.deployment = deployment
        self.msd = msd

    @property
    def passed(self):
        return all(
            step.exit_status == 0
            for step in self.msd.steps
            if hasattr(step, "exit_status")
        )

    def save(self):
        session = db.connect()
        for step in self.msd.steps:
            if hasattr(step, "exit_status"):
                result = db.Actions(
                    node=self.deployment,
                    exit_code=step.exit_status,
                    out=step.stdout,
                    err=step.stderr,
                )
                session.add(result)
                session.commit()

    def show(self):
        self.save()
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
