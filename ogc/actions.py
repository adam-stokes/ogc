import os
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path
from typing import Any, Dict

import sh

from ogc import db, enums, state
from ogc.deployer import Deployer
from ogc.log import Logger as log
from ogc.provision import choose_provisioner

if not state.app.engine:
    state.app.engine = db.connect()
    state.app.session = db.session(state.app.engine)


def launch(layout) -> int:
    try:
        log.info(f"Provisioning: {layout['name']}")
        engine = choose_provisioner(layout["provider"], env=state.app.env)
        engine.setup(layout)
        model = engine.create(layout=layout, env=state.app.env)
        log.info(f"Saved {model.instance_name} to database")
        return model.id
    except Exception as e:
        log.error(e)
        return -1


def launch_async(layouts) -> list[int]:
    with ProcessPoolExecutor() as executor:
        results = executor.map(
            launch,
            [layout.as_dict() for layout in layouts for _ in range(layout.scale)],
        )
    return results


def deploy(node: int) -> bool:
    try:
        with state.app.session as session:
            node_obj = session.query(db.Node).filter(db.Node.id == node).first() or None
            if node_obj:
                log.info(f"Deploying to: {node_obj.instance_name}")
                result = Deployer(node_obj, state.app.env).run()
                result.show()
            else:
                log.warning(f"Could not find Node (id: {node})")
                return False
    except Exception as e:
        log.error(e)
        return False
    return True


def deploy_async(nodes) -> list[bool]:
    with ProcessPoolExecutor() as executor:
        results = executor.map(deploy, [node for node in nodes if node > 0])
    return results


def teardown(
    name: str,
    force: bool = False,
    only_db: bool = False,
) -> bool:
    """Tear down node"""
    result = True
    with state.app.session as session:
        node_data = (
            session.query(db.Node).filter(db.Node.instance_name == name).first() or None
        )
        if node_data:
            log.info(f"Destroying: {node_data.instance_name}")
            if not only_db:
                try:
                    engine = choose_provisioner(node_data.provider, env=state.app.env)

                    deploy = Deployer(node_data, env=state.app.env, force=force)

                    if not force:
                        # Pull down artifacts if set
                        if node_data.artifacts:
                            log.info("Downloading artifacts")
                            local_artifact_path = (
                                Path(enums.LOCAL_ARTIFACT_PATH)
                                / node_data.instance_name
                            )
                            if not local_artifact_path.exists():
                                os.makedirs(str(local_artifact_path), exist_ok=True)
                            deploy.get(node_data.artifacts, str(local_artifact_path))

                        exec_result = deploy.exec("./teardown")
                        if not exec_result.passed:
                            log.error(
                                f"Unable to run teardown script on {node_data.instance_name}"
                            )
                    is_destroyed = deploy.node.destroy()
                    if not is_destroyed:
                        result = False
                        log.error(f"Unable to destroy {deploy.node.id}")
                except:
                    result = False
                    log.warning(f"Couldn't destroy {node_data.instance_name}")
            engine.cleanup(node_data)
            session.delete(node_data)
            session.commit()
    return result


def teardown_async(
    names: list[str], force: bool = False, only_db: bool = False
) -> list[bool]:
    if not isinstance(names, list):
        names = list(names)
    with ProcessPoolExecutor() as executor:
        func = partial(teardown, only_db=only_db, force=force)
        results = executor.map(func, names)
    return results


def sync(layout, overrides: Dict[Any, Any]) -> None:
    log.info(f"Starting deployment sync for {layout.name}...")

    override = overrides[layout.name]
    if override["action"] == "add":
        node_id = launch(layout.as_dict())
        result = deploy(node_id)
        if not result:
            log.error("Could not deploy node")

    elif override["action"] == "remove":
        with state.app.session as session:
            for data in (
                session.query(db.Node)
                .filter(db.Node.instance_name.endswith(layout.name))
                .order_by(db.Node.id.desc())
                .limit(1)
            ):
                teardown(data.instance_name, force=True)


def sync_async(layouts, overrides: Dict[Any, Any]) -> list[bool]:
    with ProcessPoolExecutor() as executor:
        func = partial(sync, overrides=overrides)
        results = executor.map(
            func,
            [
                layout
                for layout in layouts
                for _ in range(abs(overrides[layout.name]["remaining"]))
            ],
        )
    return results


def exec(node: db.Node, cmd: str) -> None:
    result = None
    with state.app.session as session:
        cmd_opts = [
            "-i",
            str(node.ssh_private_key),
            f"{node.username}@{node.public_ip}",
        ]
        cmd_opts.append(cmd)
        try:
            out = sh.ssh(cmd_opts, _env=state.app.env, _err_to_out=True)
            result = db.Actions(
                node=node,
                exit_code=out.exit_code,
                out=out.stdout.decode(),
                error=out.stderr.decode(),
            )
        except sh.ErrorReturnCode as e:
            result = db.Actions(
                node=node,
                exit_code=e.exit_code,
                out=e.stdout.decode(),
                error=e.stderr.decode(),
            )
        session.add(result)
        session.commit()
    return result.exit_code == 0


def exec_async(name: str, tag: str, cmd: str) -> list[bool]:
    rows = []
    with state.app.session as session:
        if tag:
            rows = session.query(db.Node).filter(db.Node.tags.contains([tag]))
        elif name:
            rows = session.query(db.Node).filter(db.Node.instance_name == name)
        else:
            rows = session.query(db.Node).all()

    log.info(f"Executing '{cmd}' across [green]{rows.count()}[/] nodes.")
    with ProcessPoolExecutor() as executor:
        func = partial(exec, cmd=cmd)
        results = executor.map(
            func,
            [node for node in rows],
        )
    return results


def exec_scripts(node: db.Node, path: str) -> None:
    choose_provisioner(node.provider, env=state.app.env)
    deploy = Deployer(node, env=state.app.env)
    result = deploy.exec_scripts(path)
    result.save()
    return result.passed


def exec_scripts_async(name: str, tag: str, path: str) -> list[bool]:
    rows = []
    with state.app.session as session:
        if tag:
            rows = session.query(db.Node).filter(db.Node.tags.contains([tag]))
        elif name:
            rows = session.query(db.Node).filter(db.Node.instance_name == name)
        else:
            rows = session.query(db.Node).all()

    log.info(f"Executing scripts from '{path}' across {rows.count()} nodes.")
    with ProcessPoolExecutor() as executor:
        func = partial(exec_scripts, path=path)
        results = executor.map(
            func,
            [node for node in rows],
        )
    return results
