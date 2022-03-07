# pylint: disable=unexpected-keyword-arg
import sys
from pathlib import Path

import click
import sh

from ..cache import Cache
from ..fs import walk
from ..provision import Deployer
from ..state import app
from .base import cli


@click.command(help="Login to a node")
@click.argument("name")
def ssh(name):
    cache_obj = Cache()
    node = None
    if cache_obj.exists(name):
        node = cache_obj.load(name)
    if node:
        cmd = ["-i", str(node.ssh_private_key), f"{node.username}@{node.host}"]
        sh.ssh(cmd, _fg=True, _env=app.env)
        sys.exit(0)

    app.log.error(f"Unable to locate {name} to connect to")
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
def scp_to(name, src, dst, exclude):
    cache_obj = Cache()
    node = None
    if cache_obj.exists(name):
        node = cache_obj.load(name)
    if not node:
        click.secho(f"Could not find {name} in cache", fg="red")
        sys.exit(1)
    deploy = Deployer(node)
    deploy.put(Path(src), Path(dst), excludes=exclude, msg_cb=app.log.info)


@click.command(help="Scp files or directories from node")
@click.argument("name")
@click.argument("dst")
@click.argument("src")
def scp_get(name, dst, src):
    cache_obj = Cache()
    node = None
    if cache_obj.exists(name):
        node = cache_obj.load(name)
    if not node:
        click.secho(f"Could not find {name} in cache", fg="red")
        sys.exit(1)
    deploy = Deployer(node)
    deploy.get(Path(dst), Path(src), app.log.info)


cli.add_command(ssh)
cli.add_command(scp_to)
cli.add_command(scp_get)
