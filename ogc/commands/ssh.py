# pylint: disable=unexpected-keyword-arg
import os
import sys
from pathlib import Path

import click
import sh

from ogc import actions, db, enums

from ..deployer import Deployer
from ..state import app
from .base import cli


@click.command(help="Login to a node")
@click.argument("name")
def ssh(name):
    db.connect()
    node = db.NodeModel.get(db.NodeModel.instance_name == name)
    if node:
        cmd = ["-i", str(node.ssh_private_key), f"{node.username}@{node.public_ip}"]
        sh.ssh(cmd, _fg=True, _env=app.env)
        sys.exit(0)

    app.log.error(f"Unable to locate {name} to connect to")
    sys.exit(1)


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
        click.echo(
            click.style(
                "Combined filtered options are not supported, please choose one.",
                fg="red",
            )
        )
        sys.exit(1)
    results = actions.exec(by_name, by_tag, cmd)
    if all(res for res in results):
        app.log.info("All commands completed.")
        sys.exit(0)

    app.log.error("Some commands failed to complete.")
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
    db.connect()
    node = db.NodeModel.get(db.NodeModel.instance_name == name)
    if node:
        deploy = Deployer(node, app.env)
        deploy.put(src, dst, excludes=exclude)
        sys.exit(0)
    app.log.error(f"Unable to locate {name} to connect to")
    sys.exit(1)


@click.command(help="Scp files or directories from node")
@click.argument("name")
@click.argument("dst")
@click.argument("src")
def pull_files(name, dst, src):
    db.connect()
    node = db.NodeModel.get(db.NodeModel.instance_name == name)
    if node:
        deploy = Deployer(node, app.env)
        deploy.get(dst, src)
        sys.exit(0)
    app.log.error(f"Unable to locate {name} to connect to")
    sys.exit(1)


@click.command(help="Download artifacts from node")
@click.argument("name")
def pull_artifacts(name):
    db.connect()
    node = db.NodeModel.get(db.NodeModel.instance_name == name)
    if node:
        deploy = Deployer(node, app.env)
        if node.artifacts:
            app.log.info("Downloading artifacts")
            local_artifact_path = Path(enums.LOCAL_ARTIFACT_PATH) / node.instance_name
            if not local_artifact_path.exists():
                os.makedirs(str(local_artifact_path), exist_ok=True)
            deploy.get(node.artifacts, str(local_artifact_path))
            sys.exit(0)
        else:
            app.log.error(f"No artifacts found at {node.remote_path}")
            sys.exit(1)
    app.log.error(f"Unable to locate {name} to connect to")
    sys.exit(1)


cli.add_command(ssh)
cli.add_command(push_files)
cli.add_command(pull_files)
cli.add_command(pull_artifacts)
cli.add_command(exec)
