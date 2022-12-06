from __future__ import annotations

import typing as t
from pathlib import Path

import dill
from attr import define, field
from sqlitedict import SqliteDict

from ogc import models
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


@define
class Manager:
    db_dir: Path = field(init=False)
    db: t.Any = field(init=False)

    @db_dir.default
    def _get_db_dir(self) -> Path:
        p = Path(__file__).cwd() / ".ogc-cache"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @db.default
    def _get_db(self) -> t.Any:
        return SqliteDict(
            str(self.db_dir / "data.db"),
            encode=dill.dumps,
            decode=dill.loads,
            outer_stack=False,
        )

    def nodes(self) -> t.Mapping[str, t.Any]:
        """Return a list of nodes deployed"""
        return dict(self.db)

    def add(self, node_key: str, node: models.Machine) -> None:
        """Add node to db"""
        self.db[node_key] = node

    def remove(self, node_key: str) -> None:
        """Remove node to db"""
        if node_key in dict(self.db):
            del self.db[node_key]

    def commit(self) -> None:
        """Save to db"""
        self.db.commit()

    def close(self) -> None:
        """Close db connection"""
        self.db.close()
