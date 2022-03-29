# pylint: disable=unexpected-keyword-arg
import os
import sys
from pathlib import Path

import click
import sh
from rich.console import Console

from ogc import actions, db, enums

from ..deployer import Deployer
from ..state import app
from .base import cli

console = Console()

@click.command(help="Login to a node")
@click.argument("name")
def ssh(name):
    with db.connect() as session:
        node = session.query(db.Node).filter(db.Node.instance_name == name).one()
        if node:
            cmd = ["-i", str(node.ssh_private_key), f"{node.username}@{node.public_ip}"]
            sh.ssh(cmd, _fg=True, _env=app.env)
            sys.exit(0)

    console.log(f"Unable to locate {name} to connect to", style='bold red')
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
        console.log(
                "Combined filtered options are not supported, please choose one.",
                style="bold red"
        )
        sys.exit(1)
    results = actions.exec(by_name, by_tag, cmd)
    if all(res for res in results):
        console.log("All commands completed.")
        sys.exit(0)

    console.log("Some commands failed to complete.", style='bold red')
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
        console.log(
                "Combined filtered options are not supported, please choose one.",
                style="bold red"
        )
        sys.exit(1)
    results = actions.exec_scripts(by_name, by_tag, path)
    if all(res for res in results):
        console.log("All commands completed: [green]:heavy_check_mark:[/]")
        sys.exit(0)

    console.log("Some commands [bold red]failed[/] to complete.")
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
    with db.connect() as session:
        node = session.query(db.Node).filter(db.Node.instance_name == name).one()
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
    with db.connect() as session:
        node = session.query(db.Node).filter(db.Node.instance_name == name).one()
        if node:
            deploy = Deployer(node, app.env)
            deploy.get(dst, src)
            sys.exit(0)
        console.log(f"Unable to locate {name} to connect to", style='bold red')
        sys.exit(1)


@click.command(help="Download artifacts from node")
@click.argument("name")
def pull_artifacts(name):
    with db.connect() as session:
        node = session.query(db.Node).filter(db.Node.instance_name == name).one()
        if node:
            deploy = Deployer(node, app.env)
            if node.artifacts:
                console.log("Downloading artifacts")
                local_artifact_path = Path(enums.LOCAL_ARTIFACT_PATH) / node.instance_name
                if not local_artifact_path.exists():
                    os.makedirs(str(local_artifact_path), exist_ok=True)
                deploy.get(node.artifacts, str(local_artifact_path))
                sys.exit(0)
            else:
                console.log(f"No artifacts found at {node.remote_path}", style='bold red')
                sys.exit(1)
        console.log(f"Unable to locate {name} to connect to", style='bold red')
        sys.exit(1)


cli.add_command(ssh)
cli.add_command(push_files)
cli.add_command(pull_files)
cli.add_command(pull_artifacts)
cli.add_command(exec)
cli.add_command(exec_scripts)
