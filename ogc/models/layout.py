"""Layout model"""
from __future__ import annotations

import uuid

from attr import define, field

from ogc import db


@define
class LayoutModel:
    """Layout Model

    Synopsis:

    ```python
    from ogc.deployer import init, fs

    deployment = init(
        layout_model=dict(
            instance_size="e2-standard-4",
            name="ubuntu-ogc",
            provider="google",
            remote_path="/home/ubuntu/ogc",
            runs_on="ubuntu-2004-lts",
            scale=9,
            scripts="fixtures/ex_deploy_ubuntu",
            username="ubuntu",
            ssh_private_key=fs.expand_path("~/.ssh/id_rsa_libcloud"),
            ssh_public_key=fs.expand_path("~/.ssh/id_rsa_libcloud.pub"),
            ports=["22:22", "80:80", "443:443", "5601:5601"],
            tags=[],
            labels=dict(
                division="engineering", org="obs", team="observability", project="perf"
            ),
        ),
    )

    def rerun_scripts(**kwargs: str):
        deployment.exec_scripts(**kwargs)
    ```

    Example:
        ```bash
        > ogc ubuntu.py ls -v
        # Or run a custom task `rerun_scripts`
        > ogc ubuntu.py rerun_scripts -v -o scripts=/a/different/scripts/path
        ```
    """

    instance_size: str = field()
    name: str = field()
    provider: str = field()
    remote_path: str = field()
    runs_on: str = field()
    scale: int = field()
    scripts: str = field()
    username: str = field()
    ssh_private_key: str = field()
    ssh_public_key: str = field()
    tags: list[str] = field()
    labels: dict = field()
    ports: dict = field()
    id: str = field()

    @classmethod
    def create_from_specs(cls, specs: list) -> None:
        """Creates layout objects from spec file"""
        cache = db.cache_layout_path()
        for spec in specs:
            uid = str(uuid.uuid4())
            spec["id"] = uid
            layout = LayoutModel(**spec)
            cache[uid] = db.model_as_pickle(layout)

    @classmethod
    def query(cls, **kwargs: str) -> list[LayoutModel]:
        """list layouts"""
        cache = db.cache_layout_path()
        _layouts = [
            db.pickle_to_model(cache.get(layout)) for layout in cache.iterkeys()
        ]
        _filtered_layouts = []
        if kwargs:
            for k, v in kwargs.items():
                for _layout in _layouts:
                    if getattr(_layout, k) == v:
                        _filtered_layouts.append(_layout)
        if _filtered_layouts:
            return _filtered_layouts
        return _layouts
