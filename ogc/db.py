import os
from pathlib import Path
from typing import Any

import dill
import lmdb
from attr import define, field
from safetywrap import Err, Ok, Result

from ogc import models


@define
class Manager:
    name: str
    db_dir: Path = field(default=Path(__file__).cwd() / ".ogc-cache")
    map_size: int = field(default=1099511627776)
    db: Any = field(init=False)
    users: Any = field(init=False)
    nodes: Any = field(init=False)
    actions: Any = field(init=False)

    @db.default
    def _get_db(self) -> bytes:
        if not self.db_dir.exists():
            os.makedirs(str(self.db_dir))
        return lmdb.open(str(self.db_dir / "ogcdb"), map_size=self.map_size, max_dbs=3)

    @users.default
    def _get_users_db(self) -> bytes:
        return self.db

    @nodes.default
    def _get_nodes_db(self) -> bytes:
        return self.db.open_db("nodes".encode())

    @actions.default
    def _get_actions_db(self) -> bytes:
        return self.db.open_db("actions".encode())


DBNAME = os.environ.get("DB_NAME", "ogcdb")
M = Manager(DBNAME)


def get_user() -> Result[models.User, str]:
    """Grabs the single user in the database"""
    with M.db.begin() as txn:

        def func(seq) -> models.User:
            return (
                pickle_to_model(seq[1]) if seq[0].decode().startswith("user") else None
            )

        result = filter(lambda fn: fn is not None, map(func, [k for k in txn.cursor()]))
        result = list(result)
        return (
            Ok(result[0])
            if result
            else Err("Unable to find user, make sure you have run `ogc init` first.")
        )


def get_nodes() -> Result[list[models.Node], str]:
    user = get_user().unwrap()
    _nodes: list[models.Node] = []
    with M.db.begin(db=M.nodes) as txn:
        for _, v in txn.cursor():
            model = pickle_to_model(v)
            if model.user.slug == user.slug:
                _nodes.append(model)
    return Ok(_nodes) if _nodes else Err("No nodes available")


def get_node(name: str) -> Result[models.Node, str]:
    with M.db.begin(db=M.nodes) as txn:
        for _, v in txn.cursor():
            model = pickle_to_model(v)
            if model.instance_name == name:
                return Ok(model)
    return Err(f"Unable to find node matching: {name}")


def get_actions(node: models.Node) -> Result[list[models.Actions], str]:
    _actions: list[models.Actions] = []
    with M.db.begin(db=M.actions) as txn:
        for _, v in txn.cursor():
            model = pickle_to_model(v)
            if model.node.instance_name == node.instance_name:
                _actions.append(model)
    return (
        Ok(_actions)
        if _actions
        else Err(f"Unable to find node matching: {node.instance_name}")
    )


def save_nodes_result(nodes: list[models.Node]) -> None:
    with M.db.begin(db=M.nodes, write=True) as txn:
        for node in nodes:
            txn.put(node.id.encode("ascii"), model_as_pickle(node))


def save_actions_result(actions: list[models.Actions]) -> None:
    with M.db.begin(db=M.actions, write=True) as txn:
        for action in actions:
            txn.put(action.id.encode("ascii"), model_as_pickle(action))


def model_as_pickle(obj: Any) -> bytes:
    return dill.dumps(obj)


def pickle_to_model(obj: bytes) -> Any:
    return dill.loads(obj)
