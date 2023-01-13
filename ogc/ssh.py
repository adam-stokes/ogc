"""ssh tools"""
from __future__ import annotations

import os
import sys
import typing as t
from pathlib import Path

import sh

from ogc.models.machine import MachineModel


def ssh(machine: MachineModel) -> t.Mapping[str, str]:
    """ssh helper"""
    cmd = [
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-i",
        Path(machine.layout.ssh_private_key.expanduser()),
        f"{machine.layout.username}@{machine.public_ip}",
    ]
    sh.ssh(cmd, _fg=True, _env=os.environ.copy())  # type: ignore
    sys.exit(0)
