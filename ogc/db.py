from __future__ import annotations

import typing as t
from pathlib import Path

import dill
from playhouse.sqlite_ext import SqliteExtDatabase

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


def connect() -> SqliteExtDatabase:
    """Get the associated database file

    Returns:
        Connection to sqlite database
    """
    p = Path(__file__).cwd() / ".ogc-cache"
    p.mkdir(parents=True, exist_ok=True)
    return SqliteExtDatabase(
        str(p / "data.db"), pragmas=(("journal_mode", "wal"), ("foreign_keys", 1))
    )


def cache_path() -> Path:
    """Returns where to store files"""
    p = Path(__file__).cwd() / ".ogc-cache/nodes"
    p.mkdir(parents=True, exist_ok=True)
    return p
