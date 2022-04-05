import os
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from multiprocessing import cpu_count
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

# Not advertised, but available for those who seek moar power.
MAX_WORKERS = int(os.environ.get("OGC_MAX_WORKERS", cpu_count() - 1))


def launch(layout) -> int:
    """Launch a node.

    Synchronous function for launching a node in a cloud environment.

    **Synopsis:**

        from ogc.spec import SpecLoader
        from ogc import actions

        app.spec = SpecLoader.load(["/Users/adam/specs/ogc.yml"])
        node_ids_created = [actions.launch(layout.as_dict()) for layout in app.spec.layouts]

    Args:
        layout (ogc.spec.SpecProvisionLayout): The layout specification used
            when launching a node.

    Returns:
        id (int): The database row ID of the node that was deployed.
    """
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
        ids (list[int]): The database row ID's of the node(s) that were deployed.
    """

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(
            launch,
            [layout.as_dict() for layout in layouts for _ in range(layout.scale)],
        )
    return results


def deploy(node_id: int) -> bool:
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
        bool: True if successful, False otherwise.
    """

    try:
        with state.app.session as session:
            node_obj = (
                session.query(db.Node).filter(db.Node.id == node_id).first() or None
            )
            if node_obj:
                log.info(f"Deploying to: {node_obj.instance_name}")
                result = Deployer(node_obj, state.app.env).run()
                result.show()
            else:
                log.warning(f"Could not find Node (id: {node_id})")
                return False
    except Exception as e:
        log.error(e)
        return False
    return True


def deploy_async(nodes: list[int]) -> list[bool]:
    """Execute the deployment

    Asynchronous function for executing the deployment on a node.

    **Synopsis:**

        from ogc.spec import SpecLoader
        from ogc import actions

        app.spec = SpecLoader.load(["/Users/adam/specs/ogc.yml"])
        node_ids = actions.launch_async(app.spec.layouts)
        script_deploy_results = actions.deploy_async(node_ids)

    Args:
        nodes (list[int]): The node id's from the launch

    Returns:
        list[bool]: A list of booleans from result of deployment.
    """
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(deploy, [node for node in nodes if node > 0])
    return results


def teardown(
    name: str,
    force: bool = False,
    only_db: bool = False,
) -> bool:
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
    return result


def teardown_async(
    names: list[str], force: bool = False, only_db: bool = False
) -> list[bool]:
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
        list[bool]: True if teardown is successful, False otherwise.
    """

    if not isinstance(names, list):
        names = list(names)
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(teardown, only_db=only_db, force=force)
        results = executor.map(func, names)
    return results


def sync(layout, overrides: Dict[Any, Any]) -> bool:
    """Sync a deployment

    Function for syncing a deployment to correct scale.

    **Synopsis:**

        from ogc import actions, state
        layout = app.spec.layouts[0]
        result = actions.sync(layout, overrides={'elastic-agent-ubuntu': {'action': 'add', remaining: 5}})
        result == True

    Args:
        layout (ogc.spec.SpecProvisionLayout): The layout of the deployment
        overrides (dict): Override dictionary of what the new count of nodes should be

    Returns:
        bool: True if synced, False otherwise
    """

    log.info(f"Starting deployment sync for {layout.name}...")
    result = False
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
                result = teardown(data.instance_name, force=True)
    return result


def sync_async(layouts, overrides: Dict[Any, Any]) -> list[bool]:
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
        list[bool]: True if synced, False otherwise
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
    return results


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
    return result.exit_code == 0


def exec_async(name: str, tag: str, cmd: str) -> list[bool]:
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
    with state.app.session as session:
        if tag:
            rows = session.query(db.Node).filter(db.Node.tags.contains([tag]))
        elif name:
            rows = session.query(db.Node).filter(db.Node.instance_name == name)
        else:
            rows = session.query(db.Node).all()

    log.info(f"Executing '{cmd}' across [green]{rows.count()}[/] nodes.")
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


def exec_scripts_async(name: str, tag: str, path: str) -> list[bool]:
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

    log.info(f"Executing scripts from '{path}' across {rows.count()} nodes.")
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(exec_scripts, path=path)
        results = executor.map(
            func,
            [node for node in rows],
        )
    return results
