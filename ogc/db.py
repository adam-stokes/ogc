from __future__ import annotations

import typing as t
from pathlib import Path

import dill
import magicattr
from diskcache import Cache

from ogc.log import get_logger
from ogc.models.machine import MachineModel

log = get_logger("ogc.db")

dill.settings["recurse"] = True


def model_as_pickle(obj: object) -> bytes:
    """Converts model object to bytes"""
    output: bytes = dill.dumps(obj)
    return output


def pickle_to_model(obj: bytes) -> t.Any:
    """Converts pickled bytes to object"""
    return dill.loads(obj)


def cache_path() -> Cache:
    """Returns where to store files"""
    p = Path(__file__).cwd() / ".ogc-cache/nodes"
    return Cache(directory=p, size=2**30)


def query(**kwargs: str) -> list[MachineModel] | None:
    """list machines"""
    cache = cache_path()
    _machines = [pickle_to_model(cache.get(machine)) for machine in cache.iterkeys()]

    if not kwargs:
        return _machines

    _filtered_machines = []

    for _machine in _machines:
        for k, v in kwargs.items():
            try:
                if magicattr.get(_machine, str(k)) == v:
                    _filtered_machines.append(_machine)
            except AttributeError as exc:
                log.error(f"Missing attribute: {exc}")
    if _filtered_machines:
        return _filtered_machines
    return None
