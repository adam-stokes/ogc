"""layout spec"""

from __future__ import annotations

import logging

from ogc import fs, init

log = logging.getLogger("ogc")

deployment = init(
    layout_model=dict(
        instance_size="e2-standard-4",
        name="centos-ogc",
        provider="google",
        remote_path="/home/centos/ogc",
        runs_on="sles-12",
        scale=1,
        username="centos",
        ssh_private_key=fs.expand_path("~/.ssh/id_rsa_libcloud"),
        ssh_public_key=fs.expand_path("~/.ssh/id_rsa_libcloud.pub"),
        ports=["22:22", "80:80", "443:443", "5601:5601"],
        tags=[],
        labels=dict(
            division="engineering", org="obs", team="observability", project="perf"
        ),
    ),
)
