import typing as t
from pathlib import Path

import dill
from attr import define, field
from safetywrap import Err, Ok, Result

from ogc import models


def model_as_pickle(obj: object) -> bytes:
    output: bytes = dill.dumps(obj)
    return output


def pickle_to_model(obj: bytes) -> t.Any:
    return dill.loads(obj)


@define
class Manager:
    db_dir: Path = field(init=False)

    @db_dir.default
    def _get_db_dir(self) -> Path:
        p = Path(__file__).cwd() / ".ogc-cache"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def users(self) -> list[t.Any]:
        return [
            pickle_to_model(user.read_bytes()) for user in self.db_dir.glob("user-*")
        ]

    def nodes(self) -> list[t.Any]:
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


def get_user() -> Result[models.User, str]:
    """Grabs the single user in the database"""
    if not len(M.users()) > 0:
        return Err("Unable to find user, make sure you have run `ogc init` first.")
    return Ok(M.users()[0])


def get_nodes() -> Result[list[models.Node], str]:
    user = get_user().unwrap()
    _nodes: list[models.Node] = []
    for node in M.nodes():
        if node.user.slug == user.slug:
            _nodes.append(node)
    return Ok(_nodes) if _nodes else Err("No nodes available")


def get_node(name: str) -> Result[models.Node, str]:
    for node in get_nodes().unwrap():
        if node.instance_name == name:
            return Ok(node)
    return Err(f"Unable to find node matching: {name}")


def get_actions(node: models.Node) -> Result[list[models.Actions], str]:
    if not node.actions:
        return Err(f"Unable to find node matching: {node.instance_name}")
    return Ok(node.actions)
