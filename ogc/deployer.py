# pylint: disable=wrong-import-position
# pylint: disable=wrong-import-order


from __future__ import annotations

import os
import sys
import tempfile
import typing as t
from concurrent.futures import ThreadPoolExecutor, wait
from functools import partial
from multiprocessing import cpu_count
from pathlib import Path

import arrow
import sh
from libcloud.compute.deployment import (
    Deployment,
    FileDeployment,
    MultiStepDeployment,
    ScriptDeployment,
)
from mako.lookup import TemplateLookup
from mako.template import Template
from pampy import _
from pampy import match as pmatch
from rich.table import Table

from ogc import db, signals
from ogc.log import CONSOLE as con
from ogc.log import get_logger
from ogc.models.actions import ActionModel
from ogc.models.layout import LayoutModel
from ogc.models.machine import MachineModel
from ogc.provision import BaseProvisioner

# Not advertised, but available for those who seek moar power.
MAX_WORKERS = int(os.environ.get("OGC_MAX_WORKERS", cpu_count() - 1))

log = get_logger("ogc")


class Ctx(t.TypedDict):
    """Typed mapping of the context options passed into a rendered template"""

    env: t.Required[dict]
    node: t.Required[MachineModel]
    nodes: t.Required[t.Any]


def render(template: Path, context: Ctx) -> str:
    """Returns the correct deployment based on type of step

    Args:
        template: path to template file
        context: mapping of key,value to expose in template

    Returns:
        Rendered template string
    """
    fpath = template.absolute()
    lookup = TemplateLookup(
        directories=[
            str(template.parent.absolute()),
            str(template.parent.parent.absolute()),
        ]
    )
    _template = Template(filename=str(fpath), lookup=lookup)
    return str(_template.render(**context))


class MachineOpts(t.TypedDict):
    """Applicable options to filter machines by

    Example:
        ``` bash
        ogc fixtures/layout/ubuntu exec -v -o cmd='hostname -i' -o instance_name=ogc-ubuntu-ogc-a19a-004
        ```
    """

    instance_id: t.NotRequired[str]
    instance_name: t.NotRequired[str]
    limit: t.NotRequired[int]


def __filter_machines(**kwargs: MachineOpts) -> list[MachineModel]:
    """Filters machines by instance_id or all if none is provided

    Args:
        kwargs: Machine filter options

    Returns:
        List of machines
    """
    return t.cast(
        list[MachineModel],
        pmatch(
            kwargs,
            {"instance_id": _},
            lambda x: [MachineModel.get_or_none(MachineModel.instance_id == x)],
            {"instance_name": _},
            lambda x: [MachineModel.get_or_none(MachineModel.instance_name == x)],
            {"limit": _},
            lambda x: [node for node in MachineModel.select().limit(x)],
            _,
            [node for node in MachineModel.select()],
        ),
    )


@signals.ssh.connect
def ssh_hook(provisioner: BaseProvisioner, **kwargs: MachineOpts) -> None:
    return ssh(provisioner, **kwargs)


def ssh(provisioner: BaseProvisioner, **kwargs: MachineOpts) -> None:
    """Opens SSH connection to a machine

    Pass in a mapping of options to filter machines, a single machine
    must be queried

    Args:
        provisioner: provisioner
        kwargs: Mapping of options to pass to `ssh`

    Example:
        ``` bash
        > ogc ubuntu.py ssh -v -o instance_id=5407368969918077947
        ```
    """
    nodes = __filter_machines(**kwargs)
    if nodes:
        machine = nodes[0]
        if machine:
            cmd = [
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-i",
                Path(machine.layout.ssh_private_key).expanduser(),
                f"{machine.layout.username}@{machine.public_ip}",
            ]

            sh.ssh(cmd, _fg=True, _env=os.environ.copy())  # type: ignore
            sys.exit(0)
    log.error("Could not find machine to ssh to")
    sys.exit(1)


@signals.up.connect
def up_hook(provisioner: BaseProvisioner, **kwargs: MachineOpts) -> bool:
    """Signal hook for bringing up deployment"""
    return up(provisioner, **kwargs)


def up(provisioner: BaseProvisioner, **kwargs: MachineOpts) -> bool:
    """Bring up machines

    Args:
        provisioner: provisioner
        kwargs: Mapping of options to pass to `up`

    Returns:
        True if successful, False otherwise.
    """
    log.info("Bringing up machines")
    provisioner.setup()
    provisioner.create()
    return True


@signals.down.connect
def down_hook(provisioner: BaseProvisioner, **kwargs: MachineOpts) -> bool:
    return down(provisioner, **kwargs)


def down(provisioner: BaseProvisioner, **kwargs: MachineOpts) -> bool:
    """Tear down machines

    Pass in a **optional** mapping of options to filter machines

    Args:
        provisioner: Provisioner
        kwargs: Mapping of options to pass to `down`

    Example:
        ``` bash
        # All  machines
        > ogc ubuntu.py down -v
        # Single machine
        > ogc ubuntu.py down -v -o instance_id=5407368969918077947
        ```
    Returns:
        True if successful, False otherwise.
    """
    nodes = __filter_machines(**kwargs)
    kwargs.update({"cmd": "./teardown"})
    if not exec(provisioner, **kwargs):
        log.debug("Could not run teardown script")
    provisioner.destroy(nodes=nodes)
    for machine in nodes:
        log.info(f"Deleting data for {machine.instance_name}")
        machine.delete_instance()
    return True


@signals.ls.connect
def ls_hook(
    provisioner: BaseProvisioner, **kwargs: MachineOpts
) -> list[MachineModel] | None:
    return ls(provisioner, **kwargs)


def ls(
    provisioner: BaseProvisioner, **kwargs: MachineOpts
) -> list[MachineModel] | None:
    """Return a list of machines for deployment

    Pass in a mapping of options to filter machines

    Args:
        provisioner: Provisioner
        kwargs: Mapping of options to pass to `ls`

    Additional Options:

        |Key|Value|
        |---|-----|
        | output_file | Where to store status output, filename can end with .html or .svg |
        | suppress_output | Whether to print out the table or just return results

    Example:
        ``` bash
        > ogc ubuntu.py ls -v -o limit=8
        ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
        ┃ ID                             ┃ Name                                 ┃ Created            ┃ Status       ┃ Labels                                                                                      ┃ Connection                                                                                   ┃
        ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
        │ 5407368969918077947            │ ogc-ubuntu-ogc-f664-000              │ an hour ago        │ running      │ division=engineering,org=obs,team=observability,project=perf                                │ ssh -i /Users/adam/.ssh/id_rsa_libcloud ubuntu@34.134.169.153                                 │
        ├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ 3631668729125788664            │ ogc-ubuntu-ogc-f664-001              │ an hour ago        │ running      │ division=engineering,org=obs,team=observability,project=perf                                │ ssh -i /Users/adam/.ssh/id_rsa_libcloud ubuntu@34.133.188.125                                 │
        ├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ 3575202029581097972            │ ogc-ubuntu-ogc-f664-002              │ an hour ago        │ running      │ division=engineering,org=obs,team=observability,project=perf                                │ ssh -i /Users/adam/.ssh/id_rsa_libcloud ubuntu@104.155.176.229                                │
        ├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ 4961396037101018096            │ ogc-ubuntu-ogc-f664-003              │ an hour ago        │ running      │ division=engineering,org=obs,team=observability,project=perf                                │ ssh -i /Users/adam/.ssh/id_rsa_libcloud ubuntu@34.71.231.9                                    │
        ├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ 6845512080056900556            │ ogc-ubuntu-ogc-f664-004              │ an hour ago        │ running      │ division=engineering,org=obs,team=observability,project=perf                                │ ssh -i /Users/adam/.ssh/id_rsa_libcloud ubuntu@34.170.61.39                                   │
        ├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ 8257796978812902341            │ ogc-ubuntu-ogc-f664-006              │ an hour ago        │ running      │ division=engineering,org=obs,team=observability,project=perf                                │ ssh -i /Users/adam/.ssh/id_rsa_libcloud ubuntu@34.170.252.152                                 │
        ├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ 4654244594843638721            │ ogc-ubuntu-ogc-f664-007              │ an hour ago        │ running      │ division=engineering,org=obs,team=observability,project=perf                                │ ssh -i /Users/adam/.ssh/id_rsa_libcloud ubuntu@34.133.234.5                                   │
        ├────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
        │ 2604966443513535453            │ ogc-ubuntu-ogc-f664-008              │ an hour ago        │ running      │ division=engineering,org=obs,team=observability,project=perf                                │ ssh -i /Users/adam/.ssh/id_rsa_libcloud ubuntu@35.226.159.94                                  │
        └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
        Node Count: 8
        ```

        Suppressing the output is useful if you are using the framework programatically.

        ``` python title="ubuntu.py"
        from ogc.deployer import ls
        from ogc import fs, init

        deployment = init(
            layout_model=dict(
                instance_size="e2-standard-4",
                name="ubuntu-ogc",
                provider="google",
                remote_path="/home/ubuntu/ogc",
                runs_on="ubuntu-2004-lts",
                scale=9,
                scripts="fixtures/ex_deploy_ubuntu",
                username="ubuntu",
                ssh_private_key=fs.expand_path("~/.ssh/id_rsa_libcloud"),
                ssh_public_key=fs.expand_path("~/.ssh/id_rsa_libcloud.pub"),
                ports=["22:22", "80:80", "443:443", "5601:5601"],
                tags=[],
                labels=dict(
                    division="engineering", org="obs", team="observability", project="perf"
                ),
            ),
        )


        def uname(**kwargs: str):
            kwargs.update({"cmd": "uname -a"})
            output = exec(deployment, **kwargs)
            if output:
                print("commands executed successfully")
        ```

        Execute the above:
        ```bash title="bash -c"
        > ogc ubuntu.py uname -v
        [19:20:14] INFO     Establing provider connection...                                                              
        [19:20:25] INFO     Executing commands across 1 node(s)                                                           
        [19:20:27] DEBUG    {'exit_code': 0, 
                             'out': "Linux ogc-ubuntu-ogc-bb60-000 5.15.0-1027-gcp #34~20.04.1-Ubuntu SMP Mon Jan 9 \
                                        18:40:09 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux\n", 
                             'error': '', 
                             'cmd': '/usr/bin/ssh -o StrictHostKeyChecking=no -o \
                                                     UserKnownHostsFile=/dev/null \
                                                         -i /root/.ssh/id_ed25519 \
                                                     ubuntu@34.27.170.121 uname -a'}                                                                                
        commands executed successfully
        ```

    Returns:
        List of deployed machines
    """

    def ui_nodes_table(
        nodes: list[MachineModel], output_file: str | None = None
    ) -> None:
        con.record = True
        rows = nodes
        rows_count = len(rows)

        table = Table(
            caption=f"Node Count: [green]{rows_count}[/]",
            header_style="yellow on black",
            caption_justify="left",
            expand=True,
            width=con.width,
            show_lines=True,
        )
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Created")
        table.add_column("Status")
        table.add_column("Labels")
        table.add_column("Connection", style="bold red on black")

        for data in rows:
            table.add_row(
                data.instance_id,
                data.instance_name,
                arrow.get(data.created).humanize(),
                data.instance_state,
                ",".join(
                    [f"[purple]{k}[/]={v}" for k, v in data.layout.labels.items()]
                ),
                f"ssh -i {Path(data.layout.ssh_private_key).expanduser()} {data.layout.username}@{data.public_ip}",
            )

        con.print(table, justify="center")
        if output_file:
            if output_file.endswith("svg"):
                con.save_svg(output_file, title="Node List Output")
            elif output_file.endswith("html"):
                con.save_html(output_file)
            else:
                log.error(
                    f"Unknown extension for {output_file}, must end in '.svg' or '.html'"
                )
        con.record = False

    log.info("Querying database for machines")

    nodes = __filter_machines(**kwargs)
    if "suppress_output" not in kwargs:
        ui_nodes_table(nodes=nodes, output_file=kwargs.get("output_file", None))
    return nodes if nodes else None


@signals.exec.connect
def exec_hook(provisioner: BaseProvisioner, **kwargs: MachineOpts) -> bool:
    return exec(provisioner, **kwargs)


def exec(provisioner: BaseProvisioner, **kwargs: MachineOpts) -> bool:
    """Execute commands on node(s)

    Args:
        provisioner: provisioner
        kwargs: Options to exec

    Additional Options:
        |Key|Value|
        |---|-----|
        | cmd | command to execute on remote machines |

    Example:
        ``` bash
        > ogc ubuntu.py exec -v -o cmd='ls -l'
        # Single machine
        > ogc ubuntu.py exec -v -o cmd='ls -l' -o instance_id=2349146264239594441
        ```

    Returns:
        True if succesful, False otherwise.
    """
    cmd: str | None = None
    nodes: list[MachineModel] | None = None
    if "cmd" in kwargs:
        cmd = kwargs["cmd"]

    nodes = __filter_machines(**kwargs)

    log.info(f"Executing commands across {len(nodes)} node(s)")

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
                cmd=" ".join(txt.decode() for txt in out.cmd),
            )
        except sh.ErrorReturnCode as e:
            return_status = dict(
                exit_code=e.exit_code,
                out=e.stdout.decode(),
                error=e.stderr.decode(),
                cmd=str(e.full_cmd),
            )
        if return_status:
            log.debug(return_status)
            action = ActionModel(
                machine=_node,
                exit_code=return_status["exit_code"],
                out=return_status["out"],
                err=return_status["error"],
                cmd=str(return_status["cmd"]),
            )
            action.save()
            return bool(return_status["exit_code"] == 0)
        return False

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
def exec_scripts_hook(
    provisioner: BaseProvisioner,
    **kwargs: MachineOpts,
) -> bool:
    return exec_scripts(provisioner, **kwargs)


def exec_scripts(
    provisioner: BaseProvisioner,
    **kwargs: MachineOpts,
) -> bool:
    """Execute scripts

    Executing scripts/templates on a node.

    Args:
        provisioner: provisioner
        kwargs: Options to exec_scripts

    Additional Options:
        |Key|Value|
        |---|-----|
        | scripts | custom scripts path to execute |

    Example:
        ``` bash
        > ogc ubuntu.py exec_scripts -v -o scripts='/home/ubuntu/new-deploy-scripts'
        # Optionally, run the scripts defined in the layout
        > ogc ubuntu.py exec_scripts -v
        ```
    Returns:
        True if succesful, False otherwise.
    """
    scripts: str | None = None
    nodes: list[MachineModel] | None = None
    if "scripts" in kwargs:
        scripts = kwargs["scripts"]

    nodes = __filter_machines(**kwargs)

    log.info(f"Executing scripts across {len(nodes)} node(s)")

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
