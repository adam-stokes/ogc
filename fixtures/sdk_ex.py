"""layout spec"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait
from functools import partial
from multiprocessing import cpu_count

from ogc import fs
from ogc.deployer import down, up
from ogc.log import get_logger
from ogc.models.layout import LayoutModel
from ogc.provision import choose_provisioner

MAX_WORKERS = int(cpu_count() - 1)

log = get_logger("ogc")

# pull this from supported matrix table
supported_versions = [
    ("elastic-agent-7.17.x", ["centos-9", "debian-10", "ubuntu-2004-lts"]),
    ("elastic-agent-7.16.x", ["centos-9", "debian-10", "ubuntu-2004-lts"]),
    ("elastic-agent-7.15.x", ["centos-9", "debian-10", "ubuntu-2004-lts"]),
    ("elastic-agent-8.7.x", ["centos-9", "debian-10", "ubuntu-2004-lts"]),
    ("elastic-agent-8.6.x", ["centos-9", "debian-10", "ubuntu-2004-lts"]),
    ("elastic-agent-8.5.x", ["debian-10", "ubuntu-2004-lts"]),
]

common_layout_opts = dict(
    instance_size="e2-standard-4",
    name="ogc",
    provider="google",
    username="ogc",
    scale=1,
    ssh_private_key=fs.expand_path("~/.ssh/id_rsa_libcloud"),
    ssh_public_key=fs.expand_path("~/.ssh/id_rsa_libcloud.pub"),
    ports=["22:22", "80:80", "443:443", "5601:5601"],
    tags=[],
    labels=dict(
        division="engineering", org="obs", team="observability", project="perf"
    ),
)

layouts = []
for version, oses in supported_versions:
    for os in oses:
        opts = common_layout_opts.copy()
        opts.update(
            {
                "scripts": "fixtures/ex_deploy_ubuntu",
                "remote_path": "/home/ogc",
                "runs_on": os,
            }
        )
        layout, _ = LayoutModel.get_or_create(**opts)
        layouts.append(layout)


def deploy(layout: LayoutModel) -> None:
    provisioner = choose_provisioner(layout=layout)
    up(provisioner=provisioner)


def destroy(layout: LayoutModel) -> None:
    provisioner = choose_provisioner(layout=layout)
    down(provisioner=provisioner)


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(deploy)
        results = [executor.submit(func, layout) for layout in layouts]
        wait(results, timeout=5)
