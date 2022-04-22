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
    user: models.User
    db: Any


class Deployer:
    def __init__(self, deployment: models.Node, force: bool = False):
        self.deployment = deployment
        self.user = self.deployment.user
        self.env = self.user.env
        self.force = force

        engine = choose_provisioner(
            name=self.deployment.layout.provider,
            layout=self.deployment.layout,
            user=self.user,
        )
        self.node = engine.node(instance_id=self.deployment.instance_id)
        self._ssh_client = self._connect()

    @retry(tries=5, delay=5, backoff=1)
    def _connect(self) -> ParamikoSSHClient:
        _client = ParamikoSSHClient(
            self.deployment.public_ip,
            username=self.deployment.layout.username,
            key=str(self.deployment.layout.ssh_private_key.expanduser()),
            timeout=300,
        )
        _client.connect()
        return _client

    def render(self, template: Path, context: dict[str, str]) -> str:
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

    def exec(self, cmd: str) -> Result[models.DeployResult, Exception]:
        """Runs a command on the node"""
        script = ScriptDeployment(cmd)
        msd = MultiStepDeployment([script])
        try:
            msd.run(self.node, self._ssh_client)
        except Exception as e:
            return Err(e)

        result = models.DeployResult(node=self.deployment, msd=msd)
        return Ok(result)

    def exec_scripts(self, script_dir: str) -> Result[models.DeployResult, str]:
        scripts = Path(script_dir)
        if not scripts.exists():
            return Err("No deployment scripts found, skipping.")

        context = Ctx(
            env=self.env, node=self.deployment, user=db.get_user().unwrap(), db=db
        )

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
            return Ok(models.DeployResult(self.deployment, msd))
        return Err("Unable to initiate deployment result")

    def run(self) -> Result[models.DeployResult, str]:
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

    def put(self, src: str, dst: str, excludes: list[str], includes: list[str] = []):
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
            retry_call(sh.rsync, fargs=cmd_opts, tries=3, delay=5, backoff=1)  # type: ignore
        except sh.ErrorReturnCode as e:
            log.error(f"Unable to upload files: {e.stderr}")

    def get(self, dst: str, src: str):
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
            retry_call(sh.rsync, fargs=cmd_opts, tries=3, delay=5, backoff=1)  # type: ignore
        except sh.ErrorReturnCode as e:
            log.error(f"Unable to download files: {e.stderr}")


def show_result(model: models.DeployResult) -> None:
    log.info("Deployment Result: ")
    toolz.thread_last(
        toolz.filter(lambda step: hasattr(step, "exit_status"), model.msd.steps),
        lambda step: log.info(f"  - ({step.exit_status}): {step}"),
    )

    log.info("Connection Information: ")
    log.info(f"  - Node: {model.node.instance_name} {model.node.instance_state}")
    log.info(
        (
            f"  - ssh -i {model.node.layout.ssh_private_key.expanduser()} "
            f"{model.node.layout.username}@{model.node.public_ip}"
        )
    )


def is_success(model: models.DeployResult) -> bool:
    return all(
        step.exit_status == 0
        for step in model.msd.steps
        if hasattr(step, "exit_status")
    )


def convert_msd_to_actions(results: list[models.DeployResult]) -> list[models.Actions]:
    """Converts results from `MultistepDeployment` to `models.Actions`"""
    _results = []
    for dp in results:
        for step in dp.msd.steps:
            if hasattr(step, "exit_status"):
                log.info(f"{dp.node.instance_name} :: recording action result: {step}")
                _results.append(
                    models.Actions(
                        exit_code=step.exit_status,
                        out=step.stdout,
                        error=step.stderr,
                        node=dp.node,
                    )
                )
    log.info(f"Recorded {len(_results)} action results in database.")
    return _results
