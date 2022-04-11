import os
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from multiprocessing import cpu_count
from pathlib import Path
from typing import Any, Iterator

import sh
from pampy import match
from safetywrap import Err, Ok, Result
from toolz.functoolz import thread_last

from ogc import db, enums, spec, state
from ogc.deployer import Deployer
from ogc.log import Logger as log
from ogc.provision import choose_provisioner

if not state.app.engine:
    state.app.engine = db.connect()
    state.app.session = db.session(state.app.engine)

# Not advertised, but available for those who seek moar power.
MAX_WORKERS = int(os.environ.get("OGC_MAX_WORKERS", cpu_count() - 1))


def launch(layout: dict[str, str]) -> Result[int, str]:
    """Launch a node.

    Synchronous function for launching a node in a cloud environment.

    **Synopsis:**

        from ogc.spec import SpecLoader
        from ogc import actions

        app.spec = SpecLoader.load(["/Users/adam/specs/ogc.yml"])
        node_ids_created = [actions.launch(layout.as_dict())
                            for layout in app.spec.layouts]

    Args:
        layout (dict[str, str]): The layout specification used
            when launching a node.

    Returns:
        Result[int, str]: DB Row ID if successful, Error otherwise.
    """
    try:
        log.info(f"Provisioning: {layout['name']}")
        engine = choose_provisioner(layout["provider"], env=state.app.env)
        engine.setup(layout)
        model = engine.create(layout=layout, env=state.app.env)
        log.info(f"Saved {model.instance_name} to database")
        return Ok(int(model.id))
    except Exception as e:
        return Err(f"Failed to launch node: {e}")


def launch_async(
    layouts: list[spec.SpecProvisionLayout],
) -> Iterator[int]:
    """Launch a node asynchronously.

    Asynchronous function for launching a node in a cloud environment.

    **Synopsis:**

        from ogc.spec import SpecLoader
        from ogc import actions

        app.spec = SpecLoader.load(["/Users/adam/specs/ogc.yml"])
        node_ids_created = actions.launch_async(app.spec.layouts)

    Args:
        layouts (list[ogc.spec.SpecProvisionLayout]): The layout specification used
            when launching a node.

    Returns:
        ids (Iterator[int]): The database row ID's of the node(s) that were deployed.
    """

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(
            launch,
            [layout.as_dict() for layout in layouts for _ in range(layout.scale)],
        )
        return (result.unwrap() for result in results)


def deploy(node_id: int) -> Result[bool, str]:
    """Execute the deployment

    Function for executing the deployment on a node.

    **Synopsis:**

        from ogc.spec import SpecLoader
        from ogc import actions

        app.spec = SpecLoader.load(["/Users/adam/specs/ogc.yml"])
        layout = app.spec.layouts[0]
        node_ids = actions.launch(layout.as_dict())
        script_deploy_results = actions.deploy(node_id)

    Args:
        node (int): The node ID from the launch

    Returns:
        Result[bool, str]: `Result` with True if successful, False otherwise.
    """

    try:
        with state.app.session as session:
            node_obj = (
                session.query(db.Node).filter(db.Node.id == node_id).first() or None
            )
            if not node_obj:
                return Err("Failed to query node")
            log.info(f"Deploying to: {node_obj.instance_name}")
            result = Deployer(node_obj, state.app.env).run()
            result.show()
    except Exception as e:
        log.error(e)
        return Err(str(e))
    return Ok(True)


def deploy_async(nodes: Iterator[int]) -> Result[Iterator[bool], str]:
    """Execute the deployment

    Asynchronous function for executing the deployment on a node.

    **Synopsis:**

        from ogc.spec import SpecLoader
        from ogc import actions

        app.spec = SpecLoader.load(["/Users/adam/specs/ogc.yml"])
        node_ids = actions.launch_async(app.spec.layouts)
        script_deploy_results = actions.deploy_async(node_ids)

    Args:
        nodes (Iterator[Result[int, Error]]): The `Result` from the launch

    Returns:
        Result[Iterator[bool], Error]: A `Result` containing Iterator of
            booleans on success, Failure otherwise.
    """
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(deploy, [node for node in nodes if node > 0])
        if any(result for result in results if result.is_ok()):
            return Err("Some nodes failed to deploy scripts")
    return Ok((result.unwrap() for result in results if result.is_ok()))


def teardown(
    name: str,
    force: bool = False,
    only_db: bool = False,
) -> Result[bool, str]:
    """Teardown deployment

    Function for tearing down a node.

    **Synopsis:**

        from ogc import actions
        name = "ogc-234342-elastic-agent-ubuntu"
        is_down = actions.teardown(name, force=True)

    Args:
        name (str): The node name to teardown
        force (bool): Force
        only_db (bool): Will remove from database regardless of cloud state. Use with
            caution.

    Returns:
        bool: True if teardown is successful, False otherwise.
    """
    result = True
    with state.app.session as session:
        node_data = (
            session.query(db.Node).filter(db.Node.instance_name == name).first() or None
        )
        if node_data:
            log.info(f"Destroying: {node_data.instance_name}")
            if not only_db:
                try:
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
            session.delete(node_data)
            session.commit()
    return Ok(result) if result else Err("Failed to teardown node")


def teardown_async(
    names: list[str], force: bool = False, only_db: bool = False
) -> Result[Iterator[bool], str]:
    """Teardown deployment

    Async function for tearing down a node.

    **Synopsis:**

        from ogc import actions
        names = ["ogc-234342-elastic-agent-ubuntu", "ogc-abce34-kibana-ubuntu"]
        is_down = actions.teardown_async(names, force=True)

    Args:
        name (list[str]): The node name to teardown
        force (bool): Force
        only_db (bool): Will remove from database regardless of cloud state. Use with
            caution.

    Returns:
        Result[Iterator[bool], Error]: `Result` of Iterator[bool] if successfull, Error otherwise.
    """

    if not isinstance(names, list):
        names = list(names)
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(teardown, only_db=only_db, force=force)
        results = executor.map(func, names)
        if any(result for result in results if result.is_err()):
            return Err("Failed to teardown node")
    return Ok((result.unwrap() for result in results if result.is_ok()))


def sync(layout, overrides: dict[str, str]) -> Result[bool, str]:
    """Sync a deployment

    Function for syncing a deployment to correct scale.

    **Synopsis:**

        from ogc import actions, state
        layout = app.spec.layouts[0]
        result = actions.sync(layout, overrides={'elastic-agent-ubuntu': {'action': 'add', remaining: 5}})
        result == True

    Args:
        layout (ogc.spec.SpecProvisionLayout): The layout of the deployment
        overrides (dict[str, str]): Override dictionary of what the new count of nodes should be

    Returns:
        Result[bool, str]: True if synced, False otherwise
    """

    override = overrides[layout.name]

    def _sync_add() -> Result[bool, str]:
        log.info(f"Adding deployments for {layout.name}")
        return thread_last(layout.as_dict(), launch, lambda x: x.unwrap(), deploy)

    def _sync_remove() -> Result[bool, str]:
        log.info(f"Removing deployments for {layout.name}")
        with state.app.session as session:
            data = (
                session.query(db.Node)
                .filter(db.Node.instance_name.endswith(layout.name))
                .order_by(db.Node.id.desc())
                .limit(1)
            )
            func = partial(teardown, force=True)
            return thread_last(data, lambda x: x.first().instance_name, func)

    return match(
        override,
        {"action": "add"},
        lambda x: _sync_add(),
        {"action": "remove"},
        lambda x: _sync_remove(),
    )


def sync_async(layouts, overrides: dict[Any, Any]) -> Result[Iterator[bool], str]:
    """Sync a deployment

    Async function for syncing a deployment to correct scale.

    **Synopsis:**

        from ogc import actions, state
        results = actions.sync_async(app.spec.layouts,
            overrides={'elastic-agent-ubuntu': {'action': 'add', remaining: 5}})
        all(result == True for result in results)

    Args:
        layout (ogc.spec.SpecProvisionLayout): The layout of the deployment
        overrides (dict): Override dictionary of what the new count of nodes should be

    Returns:
        Result[Iterator[bool], Error]: True if synced, False otherwise
    """

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(sync, overrides=overrides)
        results = executor.map(
            func,
            [
                layout
                for layout in layouts
                for _ in range(abs(overrides[layout.name]["remaining"]))
            ],
        )
        if any(result for result in results if result.is_err()):
            return Err("Failed to teardown nodes")
    return Ok((result.unwrap() for result in results if result.is_ok()))


def exec(node: db.Node, cmd: str) -> bool:
    """Execute command on Node

    Function for executing a command on a node.

    **Synopsis:**

        from ogc import actions, state, db
        node = db.query(db.Node).first()
        actions.exec(node, "ls -l /")
        for action in node.actions:
            print(action.exit_code, action.out, action.error)

    Args:
        node (ogc.db.Node): The node to execute a command on
        cmd (str): The command string

    Returns:
        bool: True if succesful, False otherwise
    """

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
    return bool(result.exit_code == 0)


def exec_async(name: str, tag: str, cmd: str) -> Iterator[bool]:
    """Execute command on Nodes

    Async function for executing a command on a node.

    **Synopsis:**

        from ogc import actions, state, db
        node = db.query(db.Node).filter(db.Node.tags.contains([tag]))
        results = actions.exec_async(node, "ls -l /")
        all(result == True for result in results)

    Args:
        name (str): The node name to execute a command on
        tag (str): The tag to query for nodes. Allows running commands across multiple nodes.
        cmd (str): The command string

    Returns:
        list[bool]: True if all execs complete succesfully, False otherwise.
    """
    rows = []
    count = 0
    with state.app.session as session:
        if tag:
            rows = session.query(db.Node).filter(db.Node.tags.contains([tag]))
            count = rows.count()
        elif name:
            rows = session.query(db.Node).filter(db.Node.instance_name == name)
            count = rows.count()
        else:
            rows = session.query(db.Node).all()
            count = len(rows)

    log.info(f"Executing '{cmd}' across {count} nodes.")
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(exec, cmd=cmd)
        results = executor.map(
            func,
            [node for node in rows],
        )
    return results


def exec_scripts(node: db.Node, path: str) -> bool:
    """Execute a scripts/template directory on a Node

    Function for executing scripts/templates on a node.

    **Synopsis:**

        from ogc import actions, state, db
        node = db.query(db.Node).first()
        result = actions.exec_scripts(node, "templates/deploy/ubuntu")
        result == True

    Args:
        node (ogc.db.Node): The node to execute scripts on
        path (str): The path where the scripts reside locally

    Returns:
        bool: True if succesful, False otherwise.
    """

    choose_provisioner(node.provider, env=state.app.env)
    deploy = Deployer(node, env=state.app.env)
    result = deploy.exec_scripts(path)
    result.save()
    return result.passed


def exec_scripts_async(name: str, tag: str, path: str) -> Iterator[bool]:
    """Execute a scripts/template directory on a Node

    Async function for executing scripts/templates on a node.

    **Synopsis:**

        from ogc import actions, state, db
        nodes = db.query(db.Node).all()
        results = actions.exec_scripts_async(nodes, "templates/deploy/ubuntu")
        all(result == True for result in results)

    Args:
        name (str): The node name to execute scripts on
        tag (str): The node tag to query, allows running across multiple nodes.
        path (str): The path where the scripts reside locally

    Returns:
        list[bool]: True if succesful, False otherwise.
    """
    rows = []
    with state.app.session as session:
        if tag:
            rows = session.query(db.Node).filter(db.Node.tags.contains([tag]))
        elif name:
            rows = session.query(db.Node).filter(db.Node.instance_name == name)
        else:
            rows = session.query(db.Node).all()

    log.info("Executing scripts from '%s' across {%s} nodes." % path, rows.count())
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(exec_scripts, path=path)
        results = executor.map(
            func,
            [node for node in rows],
        )
    return results
