from typing import Any, Dict, List

from celery import chord

from ogc import db, log
from ogc.tasks import do_deploy, do_destroy, do_provision, end_provision


def launch(layouts, env: Dict[str, str]) -> List[int]:
    create_jobs = [
        do_provision.s(layout.as_dict(), env)
        for layout in layouts
        for _ in range(layout.scale)
    ]

    callback = end_provision.s()
    result = chord(create_jobs)(callback)
    return result.get()


def deploy(node_ids: List[int]) -> None:
    for id in node_ids:
        do_deploy.delay(id)


def teardown(names: List[str] = None, env: Dict[str, str] = {}) -> None:
    """Tear down nodes"""
    if names:
        log.info(f"Destroying: [{', '.join(names)}]")
        for name in names:
            do_destroy.delay(name, env)
    else:
        db.connect()
        for data in db.NodeModel.select():
            log.info(f"Destroying: {data.instance_name}")
            do_destroy.delay(data.instance_name, env)


def sync(layouts, overrides: Dict[Any, Any], env: Dict[str, str]) -> None:
    for layout in layouts:
        override = overrides[layout.name]
        if override["action"] == "add":
            create_jobs = [
                do_provision.s(layout.as_dict(), env)
                for _ in range(override["remaining"])
            ]

            callback = end_provision.s()
            result = chord(create_jobs)(callback)
            deploy(result.get())
        elif override["action"] == "remove":
            db.connect()
            for data in (
                db.NodeModel.select()
                .where(db.NodeModel.instance_name.endswith(layout.name))
                .order_by(db.NodeModel.id)
                .limit(abs(override["remaining"]))
            ):
                log.info(f"Destroying: {data.instance_name}")
                do_destroy.delay(data.instance_name, env)
