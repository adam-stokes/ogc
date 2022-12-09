from __future__ import annotations

import typing as t
from pathlib import Path

import arrow
import dill
from attr import define, field
from rich.table import Table
from sqlitedict import SqliteDict

from ogc import models
from ogc.log import CONSOLE as con
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


# Renderers
def ui_nodes_table(output_file: str | None = None) -> None:
    con.record = True
    _db = Manager()
    _dbrows = _db.nodes()

    rows = _dbrows.values()
    rows_count = len(rows)

    table = Table(
        caption=f"Node Count: [green]{rows_count}[/]",
        header_style="yellow on black",
        caption_justify="left",
        expand=True,
        width=con.width,
        show_lines=True,
    )
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Created")
    table.add_column("Status")
    table.add_column("Labels")
    table.add_column("Connection", style="bold red on black")

    for data in rows:
        table.add_row(
            data.id.split("-")[0],
            data.instance_name,
            arrow.get(data.created).humanize(),
            data.instance_state,
            ",".join([f"[purple]{k}[/]={v}" for k, v in data.layout.labels.items()]),
            f"ssh -i {data.ssh_private_key} {data.username}@{data.public_ip}",
        )

    con.print(table, justify="center")
    if output_file:
        if output_file.endswith("svg"):
            con.save_svg(output_file, title="Node List Output")
        elif output_file.endswith("html"):
            con.save_html(output_file)
        else:
            log.error(
                f"Unknown extension for {output_file}, must end in '.svg' or '.html'"
            )
    con.record = False
