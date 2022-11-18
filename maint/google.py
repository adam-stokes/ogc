#!/usr/bin/env python
"""
Maintenance script for Google. Helps clean up instances and firewalls.
"""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Iterator

import click
from click_didyoumean import DYMGroup
from libcloud.compute.base import Node as NodeType

from ogc import db
from ogc.provision import choose_provisioner
from ogc.state import app

nodes = db.get_nodes().unwrap_err()


def _destroy_async(node: str) -> None:
    """Destroys nodes"""
    engine = choose_provisioner("google", app.env)
    app.log.info(f"Removing :: {node}")
    node_res: NodeType = engine.node(instance_id=node)  # type: ignore
    if node_res:
        node_res.destroy()
    return None


def teardown(nodes: list[int]) -> Iterator[Any]:
    with ProcessPoolExecutor() as executor:
        results = executor.map(_destroy_async, [node for node in nodes])
    return results


@click.group(cls=DYMGroup)
def cli():
    pass


@click.command()
@click.option(
    "--contains", required=True, default="ogc", help="Firewall name contains string"
)
@click.option(
    "--with-delete/--no-with-delete",
    default=False,
    help="Delete found firewalls",
)
def ls_firewalls(contains, with_delete):
    """List GCP Firewalls"""
    engine = choose_provisioner("google", app.env)
    for fw in engine.list_firewalls():
        if fw.name.startswith(contains):
            if with_delete:
                click.secho(f"Deleting {fw.name}")
                engine.delete_firewall(fw.name)
            else:
                click.secho(f"Firewall found: {fw.name}")


@click.command()
@click.option(
    "--by-tag",
    required=True,
    default=f"user-{os.environ.get('USER', '')}",
    help="Tag of user",
)
@click.option(
    "--with-delete/--no-with-delete",
    default=False,
    help="Delete found instances",
)
def ls_vms(by_tag, with_delete):
    """List GCP Firewalls"""
    engine = choose_provisioner("google", app.env)
    nodes = [
        node.id
        for node in engine.provisioner.list_nodes()
        if by_tag in node.extra["tags"]
    ]
    if with_delete:
        app.log.info(f"Removing {len(nodes)} nodes ...")
        results = teardown(nodes)
        if all(result == True for result in results):
            app.log.info("All nodes removed.")
            return
        app.log.error("Some nodes could not be removed.")
        return

    for node in nodes:
        app.log.info(f"ID: {node}")


cli.add_command(ls_firewalls)
cli.add_command(ls_vms)

if __name__ == "__main__":
    cli()
