from __future__ import annotations

import typing as t
from pathlib import Path

import dill
from diskcache import Cache

from ogc.log import get_logger

log = get_logger("ogc")

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


def cache_layout_path() -> Cache:
    """Where machines are stored"""
    p = Path(__file__).cwd() / ".ogc-cache/layouts"
    return Cache(directory=p, size=2**30)
