# pylint: disable=wrong-import-position
# pylint: disable=wrong-import-order


import tempfile
from pathlib import Path
from typing import Any, TypedDict

import sh
import toolz
from libcloud.compute.deployment import (
    Deployment,
    FileDeployment,
    MultiStepDeployment,
    ScriptDeployment,
)
from libcloud.compute.ssh import ParamikoSSHClient
from mako.lookup import TemplateLookup
from mako.template import Template
from retry import retry
from safetywrap import Err, Ok, Result

from ogc import db, models
from ogc.log import Logger as log
from ogc.provision import choose_provisioner


class Ctx(TypedDict):
    env: dict
    node: models.Node
    db: Any


class Deployer:
    def __init__(self, deployment: models.Node, force: bool = False):
        self.deployment = deployment
        self.env = self.deployment.layout.env()
        self.force = force

        engine = choose_provisioner(
            name=self.deployment.layout.provider,
            layout=self.deployment.layout,
        )
        self.node = engine.node(instance_id=self.deployment.instance_id)
        if not self.node:
            return
        self._ssh_client = self._connect()

    @retry(tries=5, delay=5, backoff=5)
    def _connect(self) -> ParamikoSSHClient:
        _client = ParamikoSSHClient(
            self.deployment.public_ip,
            username=self.deployment.layout.username,
            key=str(self.deployment.layout.ssh_private_key.expanduser()),
            timeout=300,
        )
        _client.connect()
        return _client

    def render(self, template: Path, context: Ctx) -> str:
        """Returns the correct deployment based on type of step"""
        fpath = template.absolute()
        lookup = TemplateLookup(
            directories=[
                str(template.parent.absolute()),
                str(template.parent.parent.absolute()),
            ]
        )
        _template = Template(filename=str(fpath), lookup=lookup)
        return str(_template.render(**context))

    def exec(self, cmd: str) -> Result[models.Node, Exception]:
        """Runs a command on the node"""
        script = ScriptDeployment(cmd)
        msd = MultiStepDeployment([script])
        try:
            msd.run(self.node, self._ssh_client)
        except Exception as e:
            return Err(e)

        db.M.save(
            self.deployment.instance_name,
            convert_msd_to_actions(self.deployment, msd=msd),
        )
        return Ok(self.deployment)

    def exec_scripts(self, script_dir: str) -> Result[models.Node, str]:
        scripts = Path(script_dir)
        if not scripts.exists():
            return Err("No deployment scripts found, skipping.")

        context = Ctx(env=self.env, node=self.deployment, db=db)

        # teardown file is a special file that gets executed before node
        # destroy
        scripts_to_run = [
            fname for fname in scripts.glob("**/*") if fname.stem != "teardown"
        ]
        scripts_to_run.reverse()

        steps: list[Deployment] = [
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
            log.info(f"({self.deployment.instance_name}) Executing {len(steps)} steps")
            msd = MultiStepDeployment(steps)
            msd.run(self.node, self._ssh_client)
            db.M.save(
                self.deployment.instance_name,
                convert_msd_to_actions(self.deployment, msd=msd),
            )
            return Ok(self.deployment)
        return Err("Unable to initiate deployment result")

    def run(self) -> Result[models.Node, str]:
        log.info(
            f"Establishing connection ({self.deployment.public_ip}) "
            f"({self.deployment.layout.username}) ({str(self.deployment.layout.ssh_private_key)})"
        )

        # Upload any files first
        if self.deployment.layout.remote_path:
            log.info(
                f"Uploading file/directory contents to {self.deployment.instance_name}"
            )
            self.put(
                ".",
                self.deployment.layout.remote_path,
                self.deployment.layout.exclude,
                self.deployment.layout.include,
            )

        return self.exec_scripts(self.deployment.layout.scripts)

    @retry(tries=3, delay=5, backoff=5)
    def put(
        self, src: str, dst: str, excludes: list[str], includes: list[str] = []
    ) -> None:
        cmd_opts = [
            "-avz",
            "-e",
            (
                f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
                f"-i {self.deployment.layout.ssh_private_key.expanduser()}"
            ),
            src,
            f"{self.deployment.layout.username}@{self.deployment.public_ip}:{dst}",
        ]

        if includes:
            for include in includes:
                cmd_opts.append(f"--include={include}")

        if excludes:
            for exclude in excludes:
                cmd_opts.append(f"--exclude={exclude}")
        try:
            sh.rsync(cmd_opts)
        except sh.ErrorReturnCode as e:
            log.error(f"Unable to rsync: (out) {e.stdout} (err) {e.stderr}")
            return None

    @retry(tries=3, delay=5, backoff=5)
    def get(self, dst: str, src: str) -> None:
        cmd_opts = [
            "-avz",
            "-e",
            (
                f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
                f"-i {self.deployment.layout.ssh_private_key.expanduser()}"
            ),
            f"{self.deployment.layout.username}@{self.deployment.public_ip}:{dst}",
            src,
        ]
        try:
            sh.rsync(cmd_opts)
        except sh.ErrorReturnCode as e:
            log.error(f"Unable to rsync: (out) {e.stdout} (err) {e.stderr}")
            return None


def show_result(model: models.Node) -> None:
    log.info("Deployment Result: ")
    if not model.actions:
        log.error("No action results found.")
        return None

    toolz.thread_last(
        toolz.filter(lambda step: hasattr(step, "exit_code"), model.actions),
        lambda step: log.info(f"  - ({step.exit_code}): {step}"),
    )

    log.info("Connection Information: ")
    log.info(f"  - Node: {model.instance_name} {model.instance_state}")
    log.info(
        (
            f"  - ssh -i {model.layout.ssh_private_key.expanduser()} "
            f"{model.layout.username}@{model.public_ip}"
        )
    )


def is_success(node: models.Node) -> bool:
    if not node.actions:
        return False

    return all(
        step.exit_code == 0 for step in node.actions if hasattr(step, "exit_code")
    )


def convert_msd_to_actions(node: models.Node, msd: MultiStepDeployment) -> models.Node:
    """Converts results from `MultistepDeployment` to `models.Actions`"""
    for step in msd.steps:
        if hasattr(step, "exit_status"):
            log.info(f"{node.instance_name} :: recording action result: {step}")
            if node.actions:
                node.actions.append(
                    models.Actions(
                        exit_code=step.exit_status,
                        out=step.stdout,
                        error=step.stderr,
                    )
                )
            else:
                node.actions = [
                    models.Actions(
                        exit_code=step.exit_status,
                        out=step.stdout,
                        error=step.stderr,
                    )
                ]
    assert node.actions is not None
    log.info(f"Recorded {len(msd.steps)} action results.")
    return node
