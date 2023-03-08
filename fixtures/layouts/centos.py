"""layout spec"""

from __future__ import annotations

from ogc import fs, get_logger, init

log = get_logger("ogc")

deployment = init(
    layout_model=dict(
        instance_size="e2-standard-4",
        name="centos-ogc",
        provider="google",
        remote_path="/home/centos/ogc",
        runs_on="sles-12",
        scale=1,
        scripts="fixtures/ex_deploy_sles",
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
