import typing as t
from pathlib import Path

import dill
import magicattr
import structlog
from diskcache import Cache

from ogc.models.machine import MachineModel

log = structlog.getLogger()

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


def registry_path() -> Cache:
    """Returns where to store service registry"""
    p = Path(__file__).cwd() / ".ogc-cache/registry"
    return Cache(directory=p, size=2**30)


def query(**kwargs: str) -> list[MachineModel] | None:
    """list machines"""
    cache = cache_path()
    _machines = [pickle_to_model(cache.get(machine)) for machine in cache.iterkeys()]

    log.debug(kwargs)
    if not kwargs:
        return _machines

    _filtered_machines = []

    for _machine in _machines:
        for k, v in kwargs.items():
            try:
                if magicattr.get(_machine, str(k)) == v:
                    _filtered_machines.append(_machine)
            except AttributeError as exc:
                log.error(f"Missing attribute: {exc}", k=k, v=v, machine=_machine)
    if _filtered_machines:
        return _filtered_machines
    return None
