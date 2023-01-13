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
from libcloud.compute.deployment import (
    Deployment,
    FileDeployment,
    MultiStepDeployment,
    ScriptDeployment,
)
from mako.lookup import TemplateLookup
from mako.template import Template

from ogc import db, signals
from ogc.log import get_logger
from ogc.models.actions import ActionModel
from ogc.models.layout import LayoutModel
from ogc.models.machine import MachineModel
from ogc.provision import BaseProvisioner

# Not advertised, but available for those who seek moar power.
MAX_WORKERS = int(os.environ.get("OGC_MAX_WORKERS", cpu_count() - 1))

log = get_logger("ogc")


class Ctx(t.TypedDict):
    env: t.Required[dict]
    node: t.Required[MachineModel]
    nodes: t.Required[t.Any]


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


@signals.up.connect
def up(provisioner: BaseProvisioner, **kwargs: str) -> bool:
    """Bring up machines

    Returns:
        True if successful, False otherwise.
    """
    log.info("Bringing up machines")
    provisioner.setup()
    provisioner.create()
    return True


@signals.down.connect
def down(provisioner: BaseProvisioner, **kwargs: str) -> bool:
    """Tear down machines

    Returns:
        True if successful, False otherwise.
    """
    if not exec(provisioner, cmd="./teardown"):
        log.debug("Could not run teardown script")
    nodes = [node for node in MachineModel.select()]
    provisioner.destroy(nodes=nodes)
    for machine in MachineModel.select():
        machine.delete_instance()
    return True


@signals.ls.connect
def ls(provisioner: BaseProvisioner, **kwargs: str) -> list[MachineModel] | None:
    """Return a list of machines for deployment

    Pass in a mapping of options to filter machines

    Args:
        limit int Set the limit of machines returned
    Returns:
        List of deployed machines
    """
    log.info("Querying database for machines")
    query = MachineModel.select()
    if "limit" in kwargs:
        query = query.limit(kwargs["limit"])
    _machines = [machine for machine in query]
    log.debug(_machines)
    return _machines if _machines else None


@signals.exec.connect
def exec(provisioner: BaseProvisioner, **kwargs: str) -> bool:
    """Execute commands on node(s)

    Args:
        cmd (str): Command to run on node

    Returns:
        True if succesful, False otherwise.
    """
    cmd: str | None = None
    nodes: list[MachineModel] | None = None
    if "cmd" in kwargs:
        cmd = kwargs["cmd"]
    if "nodes" in kwargs:
        nodes = t.cast(list[MachineModel], kwargs["nodes"])

    def _exec(node: bytes, cmd: str) -> bool:
        _node: MachineModel = t.cast(MachineModel, db.pickle_to_model(node))
        cmd_opts = [
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-i",
            Path(_node.layout.ssh_private_key).expanduser(),
            f"{_node.layout.username}@{_node.public_ip}",
        ]
        cmd_opts.append(cmd)
        return_status = None
        try:
            out = sh.ssh(cmd_opts, _env=os.environ.copy(), _err_to_out=True)
            return_status = dict(
                exit_code=out.exit_code,
                out=out.stdout.decode(),
                error=out.stderr.decode(),
                cmd=out.cmd,
            )
        except sh.ErrorReturnCode as e:
            return_status = dict(
                exit_code=e.exit_code,
                out=e.stdout.decode(),
                error=e.stderr.decode(),
                cmd=e.full_cmd,
            )
        if return_status:
            log.debug(f"exit_code: {return_status['exit_code']}")
            log.debug(f"out: {return_status['out']}")
            log.debug(f"error: {return_status['error']}")
            action = ActionModel(
                machine=_node,
                exit_code=return_status["exit_code"],
                out=return_status["out"],
                err=return_status["error"],
                cmd=return_status["cmd"],
            )
            action.save()
            return bool(return_status["exit_code"] == 0)
        return False

    if not nodes:
        nodes = [node for node in MachineModel.select()]
    if cmd:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            func = partial(_exec, cmd=cmd)
            results = [
                executor.submit(func, db.model_as_pickle(node)) for node in nodes
            ]
            wait(results, timeout=5)
            return True
    return False


@signals.exec_scripts.connect
def exec_scripts(
    provisioner: BaseProvisioner,
    **kwargs: str,
) -> bool:
    """Execute scripts

    Executing scripts/templates on a node.

    Args:
        scripts The full path or directory where the scripts reside locally.
                Supports single file and directory.
        filters Filters to pass into exec, currently `name` and `tag` are supported.

    Returns:
        True if succesful, False otherwise.
    """
    scripts: str | None = None
    nodes: list[MachineModel] | None = None
    if "scripts" in kwargs:
        scripts = kwargs["scripts"]
    if "nodes" in kwargs:
        nodes = t.cast(list[MachineModel], kwargs["nodes"])

    def _exec_scripts(node: bytes, scripts: str | Path | None = None) -> bool:
        _node: MachineModel = t.cast(MachineModel, db.pickle_to_model(node))
        _scripts = Path(scripts) if scripts else Path(_node.layout.scripts)
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
            # scripts_to_run.reverse()

        context = Ctx(
            env=os.environ.copy(),
            node=_node,
            nodes=[node for node in MachineModel.select()],
        )
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
                node_state = _node.state()
                if node_state:
                    msd.run(node_state, ssh_client)
            for step in msd.steps:
                match step:
                    case FileDeployment():
                        log.debug(
                            f"(source) {step.source if hasattr(step, 'source') else ''} "
                            f"(target) {step.target if hasattr(step, 'target') else ''} "
                        )
                    case ScriptDeployment():
                        log.debug(
                            f"(exit) {step.exit_status if hasattr(step, 'exit_status') else 0} "
                            f"(out) {step.stdout if hasattr(step, 'stdout') else ''} "
                            f"(stderr) {step.stderr if hasattr(step, 'stderr') else ''}"
                        )
                        action = ActionModel(
                            machine=_node,
                            exit_code=step.exit_status
                            if hasattr(step, "exit_status")
                            else 0,
                            out=step.stdout if hasattr(step, "stdout") else "",
                            err=step.stderr if hasattr(step, "stderr") else "",
                            cmd=f"{step.script} {step.args}",
                        )
                        action.save()
                    case _:
                        log.debug(step)
        return True

    if not nodes:
        nodes = [node for node in MachineModel.select()]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(_exec_scripts, scripts=scripts)
        results = [executor.submit(func, db.model_as_pickle(node)) for node in nodes]
        wait(results, timeout=5)
        return all([res.result() is True for res in results])


def _init(layout_model: t.Mapping[str, t.Any]) -> BaseProvisioner | None:
    """Loads deployment, kicks off signal dispatch"""
    provisioner: BaseProvisioner
    layout, _ = LayoutModel.get_or_create(**layout_model)
    provisioner = signals.init.send(layout)
    if provisioner:
        return provisioner
    return None


init = partial(_init)
