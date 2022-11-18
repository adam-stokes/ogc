from __future__ import annotations

import typing as t
from pathlib import Path

import dill
from attr import define, field
from safetywrap import Err, Ok, Result

from ogc import models
from ogc.log import Logger as log

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

    @db_dir.default
    def _get_db_dir(self) -> Path:
        p = Path(__file__).cwd() / ".ogc-cache"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def nodes(self) -> list[models.Node]:
        """Return a list of nodes deployed"""
        return [
            pickle_to_model(node.read_bytes()) for node in self.db_dir.glob("ogc-*")
        ]

    def save(self, fname: str, obj: object) -> bool:
        """Store the object to a pickled fname"""
        save_path = self.db_dir / fname
        return bool(save_path.write_bytes(model_as_pickle(obj)))

    def load(self, fname: str) -> object:
        """Load pickled obj"""
        load_path = self.db_dir / fname
        return pickle_to_model(load_path.read_bytes())

    def delete(self, fname: str) -> bool:
        delete_path = self.db_dir / fname
        delete_path.unlink(missing_ok=True)
        return delete_path.exists()


M = Manager()


def get_nodes() -> Result[list[models.Node], str]:
    return Ok(M.nodes()) if len(M.nodes()) > 0 else Err("No nodes found")


def get_node(name: str) -> Result[models.Node, str]:
    nodes = get_nodes().unwrap_or_else(log.error)
    if not nodes:
        return Err("Failed to find nodes.")
    node = [node for node in nodes if node.instance_name == name]
    return Ok(node[0]) if node else Err(f"Could not find node: {name}")


def get_actions(node: models.Node) -> Result[list[models.Actions], str]:
    if not node.actions:
        return Err(f"Unable to find node matching: {node.instance_name}")
    return Ok(node.actions)
