"""module loader utils"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from .log import get_logger

log = get_logger("ogc")


def from_path(path: Path) -> object | None:
    """Loads module into intepreter"""
    path_parents = path.parent
    sys.path.insert(0, str(path_parents.resolve()))
    module = path.parts[-1]
    modname, _ = os.path.splitext(module)
    try:
        return importlib.import_module(modname)
    except ModuleNotFoundError as e:
        log.warning(f"Could not load layout: {e}")
        return None


def run(mod: object, func: str, **kwargs: str) -> None:
    """Runs the module function passing in options"""
    dep = None
    try:
        deploy = getattr(mod, "deployment")
        _, dep = deploy[0]
    except AttributeError as exc:
        log.debug(
            "Could not find deployment entry, make sure the "
            "step has `deployment = init(layout_model=dict()`",
            exc_info=exc,
        )
        sys.exit(1)

    try:
        task_cmd = getattr(mod, func)
        task_cmd(**kwargs)
    except AttributeError:
        log.debug(f"Could not find custom task {func}, searching signals...")
        try:
            sig = importlib.import_module("ogc.signals")
            task_cmd = getattr(sig, func)
            task_cmd.send(dep, **kwargs)
        except ModuleNotFoundError as e:
            log.debug("Could not find signal either, exiting.", exc_info=e)
    return None
