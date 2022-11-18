from __future__ import annotations

import os
import sys
import typing as t
from pathlib import Path
from typing import TypedDict

import tomli
from dotenv import dotenv_values
from dotty_dict import dotty
from jinja2 import BaseLoader
from jinja2.sandbox import SandboxedEnvironment
from melddict import MeldDict
from toolz import thread_last
from toolz.curried import filter

from ogc import db, models
from ogc.exceptions import SpecLoaderException
from ogc.log import Logger as log


class CountCtx(TypedDict):
    scale: int
    deployed: int
    remaining: int
    action: str


def status(plan: models.Plan) -> dict[str, CountCtx]:
    """Return the status of the plan based on whats deployed and whats remaining"""
    counts = {
        layout.name: CountCtx(scale=layout.scale, deployed=0, remaining=0, action="")
        for layout in plan.layouts
    }
    nodes = db.get_nodes().unwrap_or_else(log.error)
    if not nodes:
        sys.exit(1)
    for layout in plan.layouts:
        deployed_count = thread_last(
            nodes,
            filter(lambda x: x.instance_name.endswith(layout.name)),
            list,
            len,
        )
        remaining_count = layout.scale - int(deployed_count)
        action: str = "add" if remaining_count >= 0 else "remove"
        counts[layout.name]["deployed"] = deployed_count
        counts[layout.name]["remaining"] = remaining_count
        counts[layout.name]["action"] = action
    return counts


def is_degraded(plan: models.Plan) -> bool:
    """Returns whether there are missing deployments"""
    return any(
        stat["remaining"] > 0 or stat["remaining"] < 0 for stat in status(plan).values()
    )


def is_deployed(plan: models.Plan) -> bool:
    """Returns whether there are any deployments at all"""
    return any(stat["deployed"] > 0 for stat in status(plan).values())


def deploy_status(plan: models.Plan) -> str:
    status_text = "[bold green]Healthy[/]"
    degraded = is_degraded(plan)
    deployed = is_deployed(plan)
    if degraded and deployed:
        status_text = "[bold red]Degraded[/]"
    elif not deployed:
        status_text = "Idle"
    return status_text


def parse_layout(layout: dict, sshkeys: dict) -> models.Layout:
    name, _layout = layout
    _layout["name"] = name
    _layout["ssh_public_key"] = sshkeys["public"]
    _layout["ssh_private_key"] = sshkeys["private"]
    return models.Layout(**{key.replace("-", "_"): val for key, val in _layout.items()})


class SpecLoader(MeldDict):
    @classmethod
    def loads(cls, spec: t.Mapping[str, t.Any]) -> models.Plan:
        """loads a spec from a mapping"""
        cl = SpecLoader()
        cl += spec
        ssh_field: dict[str, Path] = cl.get("ssh-keys", cl.get("ssh_keys"))
        ssh_keys = {
            "public": Path(ssh_field["public"]),
            "private": Path(ssh_field["private"]),
        }
        layouts = [parse_layout(layout, ssh_keys) for layout in cl["layouts"].items()]
        return models.Plan(name=cl["name"], ssh_keys=ssh_keys, layouts=layouts)

    @classmethod
    def load(cls, specs: list[str | Path]) -> models.Plan:
        if Path("ogc.toml").exists():
            specs.insert(0, "ogc.toml")

        _specs = [Path(sp) for sp in specs if Path(sp).exists()]
        if not _specs:
            raise SpecLoaderException(
                "No provision specs found, please specify with `--spec <file.toml>`"
            )

        cl = SpecLoader()
        for spec in _specs:
            spec_dict = tomli.loads(spec.read_text())

            try:
                env = SandboxedEnvironment(loader=BaseLoader())
                env.globals["cwd"] = str(Path.cwd())
                env.globals["env"] = dotty({**dotenv_values(".env"), **os.environ})
                env.globals["var"] = dotty(spec_dict)
                temp = env.from_string(spec.read_text())
                cl += tomli.loads(temp.render())
            except Exception as e:
                log.error(f"Could not parse config: {e}")

        ssh_field: dict[str, Path] = cl.get("ssh-keys", cl.get("ssh_keys"))
        ssh_keys = {
            "public": Path(ssh_field["public"]),
            "private": Path(ssh_field["private"]),
        }
        layouts = [parse_layout(layout, ssh_keys) for layout in cl["layouts"].items()]
        return models.Plan(name=cl["name"], ssh_keys=ssh_keys, layouts=layouts)
