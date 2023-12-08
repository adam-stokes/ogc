# pylint: disable=wrong-import-position
# pylint: disable=wrong-import-order


from __future__ import annotations

import json
import os
import sys
import tempfile
import typing as t
from multiprocessing import cpu_count
from pathlib import Path

import arrow
import rich.console
import sh
import structlog
import yaml
from attrs import asdict, fields, filters
from gevent.pool import Pool
from libcloud.compute.deployment import (Deployment, FileDeployment,
                                         MultiStepDeployment, ScriptDeployment)
from mako.lookup import TemplateLookup
from mako.template import Template
from pampy import _
from pampy import match as pmatch
from rich.table import Table

import ogc.service
from ogc import db
from ogc.models.actions import ActionModel
from ogc.models.layout import LayoutModel
from ogc.models.machine import MachineModel
from ogc.provision import BaseProvisioner

# Not advertised, but available for those who seek moar power.
# If more than 10 cpus, limit to 9. The CI provides a lot more
# cpu's than needed
_cpu_count = cpu_count()
if _cpu_count >= 10:
    _cpu_count = 9
MAX_WORKERS = int(os.environ.get("OGC_MAX_WORKERS", _cpu_count))


log = structlog.getLogger()
pool = Pool(MAX_WORKERS)


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
    tag: t.NotRequired[str]
    yaml: t.NotRequired[bool]
    json: t.NotRequired[bool]


def filter_machines(**kwargs: MachineOpts) -> list[MachineModel] | None:
    """Filters machines by instance_id or all if none is provided

    Args:
        kwargs: Machine filter options

    Returns:
        List of machines
    """
    results = db.query(**kwargs)
    if not results:
        return None
    return results


def filter_layouts(**kwargs: MachineOpts) -> list[LayoutModel]:
    """Filters layouts

    Args:
        kwargs: Layout filter options

    Returns:
        List of layouts
    """
    return t.cast(
        list[LayoutModel],
        pmatch(
            kwargs,
            {"name": _},
            lambda x: [LayoutModel.query(name=x)],
            {"limit": _},
            lambda x: [layout for layout in LayoutModel.query()[:x]],
            {"tag": _},
            lambda x: [
                layout
                for layout in LayoutModel.query()
                if x and set(x).intersection(layout.tags)
            ],
            _,
            [layout for layout in LayoutModel.query()],
        ),
    )


def ssh(provisioner: BaseProvisioner, **kwargs: MachineOpts) -> None:
    """Opens SSH connection to a machine

    Pass in a mapping of options to filter machines, a single machine
    must be queried

    Args:
        provisioner: provisioner
        kwargs: Mapping of options to pass to `ssh`

    Example:
        ``` bash
        > ogc -v ssh -q layout.name=machine-1
        ```
    """
    nodes = filter_machines(**kwargs)
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
                f"{machine.layout.username}@{machine.node.public_ips[0]}",
            ]

            sh.ssh(cmd, _fg=True, _env=os.environ.copy())  # type: ignore
            sys.exit(0)
    log.error("Could not find machine to ssh to")
    sys.exit(1)


def up(layouts: list[LayoutModel]) -> bool:
    """Bring up machines

    Args:
        provisioner: provisioner

    Returns:
        True if successful, False otherwise.
    """

    def _up_async(layout: LayoutModel) -> None:
        provisioner = BaseProvisioner.from_layout(layout=layout)
        try:
            provisioner.setup()
            provisioner.create()
        except Exception:
            log.error("Could not bring up instance", exc_info=True)

    log.info(
        "Creating machines from layouts",
        layouts=", ".join([f"({l.name})" for l in layouts]),
    )
    for layout in layouts:
        pool.spawn(_up_async, layout)
    pool.join()

    _new_machines = ", ".join(
        [f"({m.name}:{m.username}@{m.public_ip})" for m in filter_machines()]
    )
    log.info(f"Machines ready", machines=_new_machines)
    return True


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
    nodes = filter_machines(**kwargs)
    kwargs.update({"cmd": "./teardown"})
    if not exec(provisioner, **kwargs):
        log.debug("Could not run teardown script")
    provisioner.destroy(nodes=nodes)
    return True


def ls(
    output_format: str = "table", **kwargs: MachineOpts
) -> list[MachineModel] | None:
    """Return a list of machines for deployment

    Pass in a mapping of options to filter machines

    Args:
        kwargs: Mapping of options to pass to `ls`

    Additional Options:

        |Key|Value|
        |---|-----|
        | output_format | table, yaml, json, suppress_output


    Returns:
        List of deployed machines
    """

    con = rich.console.Console(log_time=True)

    def ui_nodes_yaml(nodes: list[MachineModel]) -> None:
        con.out(
            yaml.safe_dump(
                [
                    asdict(node, filter=filters.exclude(fields(MachineModel).node, int))
                    for node in nodes
                ]
            )
        )

    def ui_nodes_json(nodes: list[MachineModel]) -> None:
        con.out(
            json.dumps(
                [
                    asdict(node, filter=filters.exclude(fields(MachineModel).node, int))
                    for node in nodes
                ],
                skipkeys=True,
                default=str,
                indent=2,
            )
        )

    def ui_nodes_list(nodes: list[MachineModel]) -> None:
        services_list = db.registry_path()
        for node in nodes:
            _services = ""
            if node.name in services_list.iterkeys():
                _services = ", ".join(
                    [srvc for srvc in db.pickle_to_model(services_list[node.name])]
                )
            con.out(
                f"{node.name}: {node.username}@{node.public_ip} | services: ({_services if _services else 'add some'})"
            )

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
        table.add_column("Tags")
        table.add_column("Connection", style="bold red on black")

        for data in rows:
            table.add_row(
                data.node.id,
                data.node.name,
                arrow.get(data.created).humanize(),
                data.node.state,
                ",".join(
                    [f"[purple]{k}[/]={v}" for k, v in data.layout.labels.items()]
                ),
                ",".join([f"[purple]{tag}[/]" for tag in data.layout.tags]),
                f"ssh -i {Path(data.layout.ssh_private_key).expanduser()} {data.layout.username}@{data.node.public_ips[0]}",
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

    nodes = filter_machines(**kwargs)
    if nodes:
        if output_format == "yaml":
            ui_nodes_yaml(nodes=nodes)
        elif output_format == "json":
            ui_nodes_json(nodes=nodes)
        elif output_format == "list":
            ui_nodes_list(nodes=nodes)
        elif output_format == "suppress_output":
            ui_nodes_table(nodes=nodes, output_file=kwargs.get("output_file", None))
        else:
            ui_nodes_table(nodes=nodes)
    return nodes if nodes else None


def ls_layouts(
    provisioner: BaseProvisioner, **kwargs: MachineOpts
) -> list[LayoutModel] | None:
    """Return a list of layouts deployment

    Pass in a mapping of options to filter layouts

    Args:
        provisioner: Provisioner
        kwargs: Mapping of options to pass to `ls`

    Additional Options:

        |Key|Value|
        |---|-----|
        | as_json | output to json |
        | as_yaml | Output as YAML |
        | suppress_output | Whether to print out the table or just return results |

    Example:
        ``` bash
        > ogc -v layout ls

    Returns:
        List of imported layouts
    """

    def ui_layouts_yaml(layouts: list[LayoutModel]) -> None:
        con.print(yaml.safe_dump([asdict(layout) for layout in layouts]))

    def ui_layouts_json(layouts: list[LayoutModel]) -> None:
        con.print(
            json.dumps(
                [asdict(layout) for layout in layouts],
                skipkeys=True,
                default=str,
                indent=2,
            )
        )

    def ui_layouts_table(layouts: list[LayoutModel]) -> None:
        con.record = True
        rows = layouts
        rows_count = len(rows)

        table = Table(
            caption=f"Layout Count: [green]{rows_count}[/]",
            header_style="yellow on black",
            caption_justify="left",
            expand=True,
            width=con.width,
            show_lines=True,
        )

        for key in asdict(rows[0]).keys():
            table.add_column(key.lower())

        for data in rows:
            data.ports = ",".join(data.ports)
            data.tags = ",".join(data.tags)
            data.labels = ",".join(data.labels)
            item = [str(i) for i in asdict(data).values()]
            table.add_row(*item)

        con.print(table, justify="center")
        con.record = False

    layouts = filter_layouts(**kwargs)
    if "yaml" in kwargs and kwargs["yaml"]:
        ui_layouts_yaml(layouts=layouts)
    elif "json" in kwargs and kwargs["json"]:
        ui_layouts_json(layouts=layouts)
    elif "suppress_output" not in kwargs:
        ui_layouts_table(layouts=layouts)
    return layouts if layouts else None


def exec(cmd: str, **kwargs: MachineOpts) -> bool:
    """Execute commands on node(s)

    Args:
        machines: list of machines to execute on
        kwargs: Options to exec

    Additional Options:
        |Key|Value|
        |---|-----|
        | cmd | command to execute on remote machines |

    Example:
        ``` bash
        > ogc -v exec 'ls -l'
        ```

    Returns:
        True if succesful, False otherwise.
    """

    def _exec(node: MachineModel, cmd: str) -> bool:
        _node: MachineModel = node
        cmd_opts = [
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-i",
            str(Path(_node.layout.ssh_private_key).expanduser()),
            f"{_node.layout.username}@{_node.node.public_ips[0]}",
        ]
        cmd_opts.append(cmd)
        return_status = None
        try:
            out = sh.ssh(cmd_opts, _env=os.environ.copy(), _err_to_out=True)
            return_status = dict(
                exit_code=0,
                out=out,
                error=out,
                cmd=" ".join(txt for txt in cmd_opts),
            )
        except sh.ErrorReturnCode as e:
            return_status = dict(
                exit_code=e.exit_code,
                out=e.stdout.decode(),
                error=e.stderr.decode(),
                cmd=str(e.full_cmd),
            )
        if return_status:
            return_status.update({"machine": _node.node.name})
            log.debug(return_status)

            action = ActionModel(
                machine=_node,
                exit_code=int(return_status["exit_code"]),
                out=str(return_status["out"]),
                err=str(return_status["error"]),
                cmd=str(return_status["cmd"]),
            )
            if action.exit_code > 0:
                log.error(
                    "Action failed",
                    cmd=action.cmd,
                    exit_code=action.exit_code,
                    err=action.err,
                )
            else:
                log.info(
                    "Action complete",
                    cmd=action.cmd,
                    exit_code=action.exit_code,
                )
            return bool(return_status["exit_code"] == 0)
        return False

    if cmd:
        machines = filter_machines(**kwargs)
        log.info(f"Executing '{cmd}' across {len(machines)} node(s)")
        for node in machines:
            pool.spawn(_exec, node, cmd)
        return bool(pool.join())
    return False


def exec_scripts(script_dir: Path, **kwargs: MachineOpts) -> bool:
    """Execute scripts

    Executing scripts/templates on a node.

    Args:
        machines: machines to execute scripts on
        kwargs: Options to exec_scripts

    Additional Options:
        |Key|Value|
        |---|-----|
        | scripts | custom scripts path to execute |

    Example:
        ``` bash
        > ogc -v exec_scripts /home/ubuntu/new-deploy-scripts
        ```
    Returns:
        True if succesful, False otherwise.
    """

    def _exec_scripts(node: MachineModel, scripts: str | Path) -> bool:
        _node: MachineModel = node
        _scripts = Path(scripts)
        if not _scripts.exists():
            return False

        if not _scripts.is_dir():
            scripts_to_run = [_scripts.resolve()]
            _plan = yaml.safe_load((_scripts.parent / ".plan.yml").read_text())
            ogc.service.add(_node, _plan["name"])
        else:
            # teardown file is a special file that gets executed before node
            # destroy
            scripts_to_run = [
                fname for fname in _scripts.glob("**/*") if fname.stem != "teardown"
            ]

        context = Ctx(
            env=os.environ.copy(),
            node=_node,
            nodes=[node for node in MachineModel.query()],
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
                node_state = _node.node
                if node_state:
                    msd.run(node_state, ssh_client)
            for step in msd.steps:
                match step:
                    case FileDeployment():
                        log.debug(
                            f"(machine) {_node.node.name} "
                            f"(source) {step.source if hasattr(step, 'source') else ''} "
                            f"(target) {step.target if hasattr(step, 'target') else ''} "
                        )
                    case ScriptDeployment():
                        log.debug(
                            f"(machine) {_node.node.name} "
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
                        log.debug(action)
                    case _:
                        log.debug(step)
        return True

    machines = filter_machines(**kwargs)
    log.info(f"Executing scripts across {len(machines)} node(s)")
    for node in machines:
        pool.spawn(_exec_scripts, node, script_dir)
    pool.join()
    return True
