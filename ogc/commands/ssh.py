# pylint: disable=unexpected-keyword-arg
import os
import sys
from pathlib import Path

import click
import sh

from ogc import actions, db, enums, state
from ogc.log import Logger as log

from ..deployer import Deployer
from .base import cli

# DB Connection
if not state.app.engine:
    state.app.engine = db.connect()
    state.app.session = db.session(state.app.engine)


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
def ssh(by_id, by_name):
    with state.app.session as session:
        if by_name:
            node = (
                session.query(db.Node).filter(db.Node.instance_name == by_name).first()
                or None
            )
        elif by_id:
            node = session.query(db.Node).filter(db.Node.id == by_id).first() or None
        else:
            log.error(
                "Unable to locate node in database, please double check spelling.",
                style="bold red",
            )
            sys.exit(1)
        if node:
            cmd = ["-i", str(node.ssh_private_key), f"{node.username}@{node.public_ip}"]
            sh.ssh(cmd, _fg=True, _env=state.app.env)
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
def exec(by_tag, by_name, cmd):
    if by_tag and by_name:
        log.error(
            "Combined filtered options are not supported, please choose one.",
            style="bold red",
        )
        sys.exit(1)
    results = actions.exec_async(by_name, by_tag, cmd)
    if all(res for res in results):
        log.info("All commands completed.")
        sys.exit(0)

    log.error("Some commands failed to complete.", style="bold red")
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
def exec_scripts(by_tag, by_name, path):
    if by_tag and by_name:
        log.error(
            "Combined filtered options are not supported, please choose one.",
            style="bold red",
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
def push_files(name, src, dst, exclude):
    with state.app.session as session:
        node = (
            session.query(db.Node).filter(db.Node.instance_name == name).first() or None
        )
        if node:
            deploy = Deployer(node, state.app.env)
            deploy.put(src, dst, excludes=exclude)
            sys.exit(0)
        log.error(f"Unable to locate {name} to connect to")
        sys.exit(1)


@click.command(help="Scp files or directories from node")
@click.argument("name")
@click.argument("dst")
@click.argument("src")
def pull_files(name, dst, src):
    with state.app.session as session:
        node = (
            session.query(db.Node).filter(db.Node.instance_name == name).first() or None
        )
        if node:
            deploy = Deployer(node, state.app.env)
            deploy.get(dst, src)
            sys.exit(0)
        log.error(f"Unable to locate {name} to connect to", style="bold red")
        sys.exit(1)


@click.command(help="Download artifacts from node")
@click.argument("name")
def pull_artifacts(name):
    with state.app.session as session:
        node = (
            session.query(db.Node).filter(db.Node.instance_name == name).first() or None
        )
        if node:
            deploy = Deployer(node, state.app.env)
            if node.artifacts:
                log.info("Downloading artifacts")
                local_artifact_path = (
                    Path(enums.LOCAL_ARTIFACT_PATH) / node.instance_name
                )
                if not local_artifact_path.exists():
                    os.makedirs(str(local_artifact_path), exist_ok=True)
                deploy.get(node.artifacts, str(local_artifact_path))
                sys.exit(0)
            else:
                log.error(f"No artifacts found at {node.remote_path}", style="bold red")
                sys.exit(1)
        log.error(f"Unable to locate {name} to connect to", style="bold red")
        sys.exit(1)


cli.add_command(ssh)
cli.add_command(push_files)
cli.add_command(pull_files)
cli.add_command(pull_artifacts)
cli.add_command(exec)
cli.add_command(exec_scripts)
