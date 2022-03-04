# pylint: disable=unexpected-keyword-arg
import sys
from pathlib import Path

import click
import sh

from ..cache import Cache
from ..provision import Deployer
from ..state import app
from .base import cli


@click.command(help="Login to a node")
@click.argument("name")
def ssh(name):
    cache_obj = Cache()
    node_data = None
    if cache_obj.exists(name):
        node_data = cache_obj.load(name)
    if node_data:
        node = node_data["node"]
        username = node_data["username"]
        host = node_data["host"]
        ssh_priv_key = node_data["ssh_private_key"]
        cmd = ["-i", str(ssh_priv_key), f"{username}@{host}"]
        sh.ssh(cmd, _fg=True, _env=app.env)
        sys.exit(0)

    app.error.log(f"Unable to locate {name} to connect to")
    sys.exit(1)


@click.command(help="Scp files or directories to node")
@click.argument("name")
@click.argument("src")
@click.argument("dst")
def scp_to(name, src, dst):
    deploy = Deployer(name)
    src = Path(src)
    dst = Path(dst)
    deploy.put(src, dst, app.log.info)


@click.command(help="Scp files or directories from node")
@click.argument("name")
@click.argument("dst")
@click.argument("src")
def scp_get(name, dst, src):
    deploy = Deployer(name)
    src = Path(src)
    dst = Path(dst)
    deploy.get(dst, src, app.log.info)


cli.add_command(ssh)
cli.add_command(scp_to)
cli.add_command(scp_get)
