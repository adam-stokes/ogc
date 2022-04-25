# pylint: disable=unexpected-keyword-arg
import os
import sys
from pathlib import Path

import click
import sh

from ogc import actions, db, enums
from ogc.log import Logger as log

from ..deployer import Deployer
from .base import cli


@click.command(help="Login to a node")
@click.option(
    "--by-id",
    required=False,
    help="Login to a node by its ID",
)
@click.option(
    "--by-name",
    required=False,
    help="Login to a node by its Name",
)
def ssh(by_id: str, by_name: str) -> None:
    rows = db.get_nodes().unwrap_or_else(log.critical)
    if not rows:
        sys.exit(1)
    if by_id:
        rows = [node for node in rows if node.id.split("-")[0] == by_id]
    elif by_name:
        rows = [node for node in rows if node.instance_name == by_name]
    else:
        log.error(
            "Unable to locate node in database, please double check spelling.",
        )
        sys.exit(1)

    node = rows[0]
    cmd = [
        "-i",
        str(node.layout.ssh_private_key.expanduser()),
        f"{node.layout.username}@{node.public_ip}",
    ]
    sh.ssh(cmd, _fg=True, _env=node.user.env)  # type: ignore
    sys.exit(0)


@click.command(help="Execute a command across node(s)")
@click.option(
    "--by-tag",
    required=False,
    help="Only run on nodes matching tag",
)
@click.option(
    "--by-name",
    required=False,
    help="Only run on nodes matching name",
)
@click.argument("cmd")
def exec(by_tag: str, by_name: str, cmd: str) -> None:
    if by_tag and by_name:
        log.error(
            "Combined filtered options are not supported, please choose one.",
        )
        sys.exit(1)
    results = actions.exec_async(by_name, by_tag, cmd)
    if all(res for res in results):
        log.info("All commands completed.")
        sys.exit(0)

    log.error("Some commands failed to complete.")
    sys.exit(1)


@click.command(help="(R)Execute a set of scripts")
@click.option(
    "--by-tag",
    required=False,
    help="Only run on nodes matching tag",
)
@click.option(
    "--by-name",
    required=False,
    help="Only run on nodes matching name",
)
@click.argument("path")
def exec_scripts(by_tag: str, by_name: str, path: str) -> None:
    if by_tag and by_name:
        log.error(
            "Combined filtered options are not supported, please choose one.",
        )
        sys.exit(1)
    results = actions.exec_scripts_async(by_name, by_tag, path)
    if all(res for res in results):
        log.info("All commands completed successfully ...")
        sys.exit(0)

    log.error("Some commands [bold red]failed[/] to complete.")
    sys.exit(1)


@click.command(help="Scp files or directories to node")
@click.argument("name")
@click.argument("src")
@click.argument("dst")
@click.option(
    "--exclude",
    required=False,
    multiple=True,
    help="Exclude files/directories when uploading",
)
def push_files(name: str, src: str, dst: str, exclude: list[str]) -> None:
    node = db.get_node(name).unwrap_or_else(log.error)
    if not node:
        log.error(f"Unable to locate {name} to connect to")
        sys.exit(1)
    deploy = Deployer(node)
    deploy.put(src, dst, excludes=exclude)
    sys.exit(0)


@click.command(help="Scp files or directories from node")
@click.argument("name")
@click.argument("dst")
@click.argument("src")
def pull_files(name: str, dst: str, src: str) -> None:
    node = db.get_node(name).unwrap_or_else(log.error)
    if not node:
        log.error(f"Unable to locate {name} to connect to")
        sys.exit(1)
    deploy = Deployer(node)
    deploy.get(dst, src)
    sys.exit(0)


@click.command(help="Download artifacts from node")
@click.argument("name")
def pull_artifacts(name: str):
    node = db.get_node(name).unwrap_or_else(log.error)
    if not node:
        log.error(f"Unable to locate {name} to connect to")
        sys.exit(1)
    deploy = Deployer(node)

    if node.layout.artifacts:
        log.info("Downloading artifacts")
        local_artifact_path = Path(enums.LOCAL_ARTIFACT_PATH) / node.instance_name
        if not local_artifact_path.exists():
            os.makedirs(str(local_artifact_path), exist_ok=True)
        deploy.get(node.layout.artifacts, str(local_artifact_path))
        sys.exit(0)
    else:
        log.error(f"No artifacts found at {node.layout.remote_path}")
        sys.exit(1)


cli.add_command(ssh)
cli.add_command(push_files)
cli.add_command(pull_files)
cli.add_command(pull_artifacts)
cli.add_command(exec)
cli.add_command(exec_scripts)
