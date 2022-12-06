# pylint: disable=wrong-import-position
# pylint: disable=wrong-import-order


from __future__ import annotations

import os
import tempfile
import typing as t
from concurrent.futures import ThreadPoolExecutor, wait
from functools import partial
from multiprocessing import cpu_count
from pathlib import Path

import sh
import toolz
from attr import define, field
from libcloud.compute.deployment import (
    Deployment,
    FileDeployment,
    MultiStepDeployment,
    ScriptDeployment,
)
from mako.lookup import TemplateLookup
from mako.template import Template
from retry import retry
from safetywrap import Err, Ok, Result

from ogc import db, models
from ogc.log import CONSOLE as con
from ogc.log import get_logger
from ogc.provision import BaseProvisioner

# Not advertised, but available for those who seek moar power.
MAX_WORKERS = int(os.environ.get("OGC_MAX_WORKERS", cpu_count() - 1))

log = get_logger("ogc")


class Ctx(t.TypedDict):
    env: t.Required[dict]
    node: t.Required[models.Machine]
    db: t.Required[t.Any]


def render(template: Path, context: Ctx) -> str:
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


@define
class Deployer:
    provisioner: BaseProvisioner
    db: t.Any
    force: bool = False
    _nodes: list[models.Machine] = field(init=False)

    @classmethod
    def from_provisioner(
        cls, provisioner: BaseProvisioner, force: bool = False
    ) -> Deployer:
        return Deployer(provisioner=provisioner, force=force, db=db.Manager())

    def up(self) -> bool:
        """Bring up machines"""
        self.provisioner.setup()
        self._nodes = t.cast(list[models.Machine], self.provisioner.create())
        return True

    def down(self) -> bool:
        """Tear down machines"""
        self.provisioner.destroy(nodes=self.db.nodes().values())
        for node_name in self.db.nodes().keys():
            self.db.remove(node_name)
        self.db.commit()
        return True

    def exec(self, cmd: str) -> Result[bool, Exception]:
        """Runs a command on the node(s)"""

        def _exec(node: bytes, cmd: str) -> bool:
            _node: models.Machine = db.pickle_to_model(node)
            cmd_opts = [
                "-i",
                str(_node.layout.ssh_private_key),
                f"{_node.layout.username}@{_node.public_ip}",
            ]
            cmd_opts.append(cmd)
            error_code = 0
            try:
                out = sh.ssh(cmd_opts, _env=os.environ.copy(), _err_to_out=True)  # type: ignore
                _node.actions.append(
                    models.Actions(
                        exit_code=out.exit_code,
                        out=out.stdout.decode(),
                        error=out.stderr.decode(),
                    )
                )
            except sh.ErrorReturnCode as e:
                error_code = e.exit_code  # type: ignore
                _node.actions.append(
                    models.Actions(
                        exit_code=e.exit_code,  # type: ignore
                        out=e.stdout.decode(),
                        error=e.stderr.decode(),
                    )
                )
            return bool(error_code == 0)

        nodes = self.db.nodes().values()
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            func = partial(_exec, cmd=cmd)
            results = [
                executor.submit(func, db.model_as_pickle(node)) for node in nodes
            ]
            wait(results, timeout=5)
        self.db.commit()
        return Ok(True)

    def exec_scripts(
        self, scripts: str | None = None, filters: t.Mapping[str, str] | None = None
    ) -> Result[bool, str]:
        """Execute scripts

        Async function for executing scripts/templates on a node.

        **Synopsis:**

        ```python
        from ogc import actions, state, db
        results = actions.exec_scripts_async(path="templates/deploy/ubuntu", filters={"name": "ogc-1"})
        all(result == True for result in results)
        ```

        Args:
            scripts (str): The full path or directory where the scripts reside locally.
                           Supports single file and directory.
            filters (Mapping[str, str]): Filters to pass into exec, currently `name` and `tag` are supported.

        Returns:
            bool: True if succesful, False otherwise.
        """

        def _exec_scripts(node: bytes, scripts: str | None = None) -> bool:
            _node: models.Machine = db.pickle_to_model(node)
            if not scripts:
                scripts = _node.layout.scripts
            _scripts = Path(scripts)
            if not _scripts.exists():
                return False

            if not _scripts.is_dir():
                scripts_to_run = [_scripts.resolve()]
            else:
                # teardown file is a special file that gets executed before node
                # destroy
                scripts_to_run = [
                    fname for fname in _scripts.glob("**/*") if fname.stem != "teardown"
                ]

            scripts_to_run.reverse()

            context = Ctx(env=os.environ.copy(), node=_node, db=self.db)
            steps: list[Deployment] = [
                ScriptDeployment(script=render(s, context), name=s.name)
                for s in scripts_to_run
                if s.is_file()
            ]

            # Add teardown script as just a filedeployment
            teardown_script = _scripts / "teardown"
            if teardown_script.exists():
                with tempfile.NamedTemporaryFile(delete=False) as fp:
                    temp_contents = render(teardown_script, context)
                    fp.write(temp_contents.encode())
                    steps.append(FileDeployment(fp.name, "teardown"))
                    steps.append(ScriptDeployment("chmod +x teardown"))

            if steps:
                msd = MultiStepDeployment(steps)
                ssh_client = _node.ssh()
                if ssh_client:
                    msd.run(_node.remote, ssh_client)
                    convert_msd_to_actions(_node, msd=msd)
                    self.db.add(_node.instance_name, _node)
            return True

        nodes = self.db.nodes().values()
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            func = partial(_exec_scripts, scripts=scripts)
            results = [
                executor.submit(func, db.model_as_pickle(node)) for node in nodes
            ]
            wait(results, timeout=5)
        self.db.commit()
        return Ok(all([res.result() is True for res in results])) or Err(
            "Unable execute scripts"
        )

    @retry(tries=3, delay=5, jitter=(5, 15), logger=None)
    def put(
        self, src: str, dst: str, excludes: list[str], includes: list[str] = []
    ) -> None:
        def _put(
            node: bytes,
            src: str,
            dst: str,
            excludes: list[str],
            includes: list[str] = [],
        ) -> None:
            _node: models.Machine = db.pickle_to_model(node)
            cmd_opts = [
                "-avz",
                "-e",
                (
                    f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
                    f"-i {_node.ssh_private_key.expanduser()}"
                ),
                src,
                f"{_node.username}@{_node.public_ip}:{dst}",
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

        nodes = self.db.nodes().values()
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            func = partial(_put, src=src, dst=dst, excludes=excludes, includes=includes)
            results = [
                executor.submit(func, db.model_as_pickle(node)) for node in nodes
            ]
            wait(results, timeout=5)

    @retry(tries=3, delay=5, jitter=(5, 15), logger=None)
    def get(self, dst: str, src: str) -> None:
        def _get(node: bytes, dst: str, src: str) -> None:
            _node: models.Machine = db.pickle_to_model(node)
            cmd_opts = [
                "-avz",
                "-e",
                (
                    f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
                    f"-i {_node.ssh_private_key.expanduser()}"
                ),
                f"{_node.username}@{_node.public_ip}:{dst}",
                src,
            ]
            try:
                sh.rsync(cmd_opts)
            except sh.ErrorReturnCode as e:
                log.error(f"Unable to rsync: (out) {e.stdout} (err) {e.stderr}")
                return None

        nodes = self.db.nodes().values()
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            func = partial(_get, dst=dst, src=src)
            results = [
                executor.submit(func, db.model_as_pickle(node)) for node in nodes
            ]
            wait(results, timeout=5)


def show_result(model: models.Machine) -> None:
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
            f"  - ssh -i {model.ssh_private_key.expanduser()} "
            f"{model.username}@{model.public_ip}"
        )
    )


def is_success(node: models.Node) -> bool:
    if not node.actions:
        return False

    return all(
        step.exit_code == 0 for step in node.actions if hasattr(step, "exit_code")
    )


def convert_msd_to_actions(
    node: models.Machine, msd: MultiStepDeployment
) -> models.Machine:
    """Converts results from `MultistepDeployment` to `models.Actions`"""
    for step in msd.steps:
        log.debug(msd.steps)
        if hasattr(step, "exit_status"):
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
    return node
