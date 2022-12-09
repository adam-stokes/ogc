"""ssh tools"""
from __future__ import annotations

import os
import sys

import sh

from ogc import db


def ssh(instance: str) -> None:
    """ssh helper"""
    _db = db.Manager()
    instance_names = _db.nodes().keys()
    node = None
    if instance in instance_names:
        node = _db.nodes()[instance]

    if node:
        cmd = [
            "-i",
            str(node.ssh_private_key.expanduser()),
            f"{node.username}@{node.public_ip}",
        ]
        sh.ssh(cmd, _fg=True, _env=os.environ.copy())  # type: ignore
        sys.exit(0)
