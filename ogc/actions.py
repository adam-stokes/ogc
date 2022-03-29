from typing import Any, Dict, List

from celery import chord

from ogc import db
from ogc.log import Logger as log
from ogc.tasks import (
    do_deploy,
    do_destroy,
    do_exec,
    do_exec_scripts,
    do_provision,
    end_exec,
    end_provision
)


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


def teardown(
    names: List[str] = None, env: Dict[str, str] = {}, force: bool = False
) -> None:
    """Tear down nodes"""
    if names:
        log.info(f"Destroying: {', '.join(names)}")
        for name in names:
            do_destroy.delay(name, env, force)
    else:
        with db.connect() as session:
            rows = session.query(db.Node)
            count = rows.count()
            total = count
            for data in rows.all():
                log.info(f"Destroying: {data.instance_name} ({count} of {total})")
                do_destroy.delay(data.instance_name, env, force)
                count = count - 1


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
            with db.connect() as session:
                for data in (
                    session.query(db.Node)
                    .filter(db.Node.instance_name.endswith(layout.name))
                    .order_by(db.Node.id)
                    .limit(abs(override["remaining"]))
                ):
                    log.info(f"Destroying: {data.instance_name}")
                    do_destroy.delay(data.instance_name, env, force=True)


def exec(name: str = None, tag: str = None, cmd: str = None) -> None:
    rows = []
    with db.connect() as session:
        if tag:
            rows = session.query(db.Node).filter(db.Node.tags.contains([tag]))
        elif name:
            rows = session.query(db.Node).filter(db.Node.instance_name == name)
        else:
            rows = session.query(db.Node).all()

    log.info(f"Executing '{cmd}' across [green]{rows.count()}[/] nodes.")

    exec_jobs = [
        do_exec.s(cmd, node.ssh_private_key, node.id, node.username, node.public_ip)
        for node in rows
    ]

    callback = end_exec.s()
    result = chord(exec_jobs)(callback)
    return result.get()


def exec_scripts(name: str = None, tag: str = None, path: str = None) -> None:
    rows = []
    with db.connect() as session:
        if tag:
            rows = session.query(db.Node).filter(db.Node.tags.contains([tag]))
        elif name:
            rows = session.query(db.Node).filter(db.Node.instance_name == name)
        else:
            rows = session.query(db.Node).all()

    log.info(f"Executing scripts from '{path}' across {rows.count()} nodes.")

    exec_jobs = [do_exec_scripts.s(node.id, path) for node in rows]

    callback = end_exec.s()
    result = chord(exec_jobs)(callback)
    return result.get()
