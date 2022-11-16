import os
import typing as t
from concurrent.futures import ThreadPoolExecutor, wait
from multiprocessing import cpu_count
from pathlib import Path

import sh
from pampy import match
from toolz.functoolz import partial

from ogc import db, enums, models, state
from ogc.deployer import Deployer
from ogc.log import Logger as log
from ogc.provision import choose_provisioner
from ogc.spec import CountCtx

# Not advertised, but available for those who seek moar power.
MAX_WORKERS = int(os.environ.get("OGC_MAX_WORKERS", cpu_count() - 1))


def launch(layout: bytes) -> bytes:
    """Launch a node.

    Synchronous function for launching a node in a cloud environment.

    **Synopsis:**

        from ogc.spec import SpecLoader
        from ogc import actions, db

        spec = SpecLoader.load(["/Users/adam/specs/ogc.toml"])
        nodes = [actions.launch(layout)
                 for layout in spec.layouts]

    Args:
        layout (bytes): `models.Layout` specification used
            when launching a node.

    Returns:
        bytes: Pickled `models.Node` Instance if successful, None otherwise.
    """
    _layout: models.Layout = db.pickle_to_model(layout)
    log.info(f"Provisioning: {_layout.name}")
    engine = choose_provisioner(name=_layout.provider, layout=_layout)
    engine.setup()
    model = engine.create()

    return db.model_as_pickle(model)


def launch_async(
    layouts: list[models.Layout], with_deploy: bool = True
) -> list[models.Node]:
    """Launch a node asynchronously.

    Asynchronous function for launching a node in a cloud environment.

    **Synopsis:**

        from ogc.spec import SpecLoader
        from ogc import actions, db, models

        spec = SpecLoader.load(["/Users/adam/specs/ogc.toml"])
        nodes = actions.launch_async(layouts=spec.layouts)

    Args:
        layouts (list[models.Layout]): The layout specification used
            when launching a node.
        with_deploy (bool): Also execute deployment scripts

    Returns:
        list[models.Node]: List of instance names launched
    """

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = [
            executor.submit(launch, db.model_as_pickle(layout))
            for layout in layouts
            for _ in range(layout.scale)
        ]
        wait(results)
        nodes: list[models.Node] = [
            db.pickle_to_model(node.result()) for node in results
        ]
        for node in nodes:
            db.M.save(node.instance_name, node)

        if with_deploy:
            log.info(f"Running deployment scripts on {len(nodes)} nodes")

            def run(node: bytes) -> bytes:
                return db.model_as_pickle(
                    Deployer(db.pickle_to_model(node)).run().unwrap()
                )

            results = [
                executor.submit(partial(run), db.model_as_pickle(node))
                for node in nodes
            ]
            wait(results)
            return [db.pickle_to_model(node.result()) for node in results]
        return nodes


def teardown(
    node: bytes,
    force: bool = False,
    only_db: bool = False,
) -> bytes:
    """Teardown deployment

    Function for tearing down a node.

    **Synopsis:**

        from ogc import actions
        name = "ogc-234342-elastic-agent-ubuntu"
        is_down = actions.teardown(name, force=True)

    Args:
        node (bytes): Pickled `models.Node` instance
        force (bool): Force
        only_db (bool): Will remove from database regardless of cloud state. Use with
            caution.

    Returns:
        bytes: Pickled `models.Node` that was removed, None otherwise.
    """
    _node: models.Node = db.pickle_to_model(node)
    log.info(f"Destroying: {_node.instance_name}")
    if not only_db:
        deploy = Deployer(_node, force=force)
        if not force:
            # Pull down artifacts if set
            if _node.layout.artifacts:
                log.info("Downloading artifacts")
                local_artifact_path = (
                    Path(enums.LOCAL_ARTIFACT_PATH) / _node.instance_name
                )
                local_artifact_path.mkdir(parents=True, exist_ok=True)
                deploy.get(_node.layout.artifacts, str(local_artifact_path))

            if not deploy.exec("./teardown").ok():
                log.error(f"Unable to run teardown script on {_node.instance_name}")

        is_destroyed = False
        if deploy.node:
            is_destroyed = deploy.node.destroy()
        if not is_destroyed:
            log.critical(f"Unable to destroy {_node.instance_name}")
        db.M.delete(_node.instance_name)

    return db.model_as_pickle(_node)


def teardown_async(
    nodes: list[models.Node],
    force: bool = False,
    only_db: bool = False,
) -> list[models.Node]:
    """Teardown deployment

    Async function for tearing down a node.

    **Synopsis:**

        from ogc import actions, db
        result = actions.teardown_async(db.M.get_nodes().unwrap(), force=True)
        assert(len(result) > 0)

    Args:
        nodes (list[models.Node]): The node name to teardown
        force (bool): Force
        only_db (bool): Will remove from database regardless of cloud state. Use with
            caution.

    Returns:
        list[models.Node]: List of instances destroyed
    """
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(teardown, only_db=only_db, force=force)
        results = [executor.submit(func, db.model_as_pickle(node)) for node in nodes]
        wait(results)
        return [db.pickle_to_model(node.result()) for node in results]


def sync(layout: bytes, overrides: dict[str, CountCtx]) -> bytes:
    """Sync a deployment

    Function for syncing a deployment to correct scale.

    **Synopsis:**

        from ogc import actions, state
        layout = app.spec.layouts[0]
        result = actions.sync(layout, overrides={'elastic-agent-ubuntu': {'action': 'add', remaining: 5}})
        result == True

    Args:
        layout (bytes): The Pickled `models.Layout`
        overrides (dict[str, str]): Override dictionary of what the new count of nodes should be

    Returns:
        bytes: True if synced, False otherwise
    """
    _layout: models.Layout = db.pickle_to_model(layout)
    override = overrides[_layout.name]

    def _sync_add() -> bytes:
        log.info(f"Adding deployments for {_layout.name}")
        return launch(layout)

    def _sync_remove() -> bytes:
        log.info(f"Removing deployments for {_layout.name}")
        for node in db.get_nodes().unwrap():
            if node.instance_name.endswith(_layout.name):
                return teardown(db.model_as_pickle(node), force=True)
        return b""

    return bytes(
        match(
            override,
            {"action": "add"},
            lambda x: _sync_add(),
            {"action": "remove"},
            lambda x: _sync_remove(),
        )
    )


def sync_async(
    layouts: list[models.Layout], overrides: dict[str, CountCtx]
) -> list[models.Node]:
    """Sync a deployment

    Async function for syncing a deployment to correct scale.

    **Synopsis:**

        from ogc import actions, state
        results = actions.sync_async(app.spec.layouts,
            overrides={'elastic-agent-ubuntu': {'action': 'add', remaining: 5}})
        all(result == True for result in results)

    Args:
        layouts (list[models.Layout]): The list of `models.Layout` of the deployment
        overrides (dict): Override dictionary of what the new count of nodes should be

    Returns:
        bool: True if synced, False otherwise
    """

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(sync, overrides=overrides)
        results = [
            executor.submit(func, db.model_as_pickle(layout))
            for layout in layouts
            for _ in range(abs(overrides[layout.name]["remaining"]))
        ]
        wait(results)
        nodes = [db.pickle_to_model(node.result()) for node in results]
        log.info(f"Running deployment scripts on {len(nodes)} nodes")

        def run(node: bytes) -> bytes:
            return db.model_as_pickle(Deployer(db.pickle_to_model(node)).run().unwrap())

        results = [
            executor.submit(partial(run), db.model_as_pickle(node)) for node in nodes
        ]
        wait(results)
        return [db.pickle_to_model(node.result()) for node in results]


def exec(node: bytes, cmd: str) -> bool:
    """Execute command on Node

    Function for executing a command on a node.

    **Synopsis:**

        from ogc import actions, state, db
        node = db.get_nodes().unwrap()[0]
        actions.exec(node, "ls -l /")
        for action in node.actions:
            print(action.exit_code, action.out, action.error)

    Args:
        node (models.Node): The `models.Node` to execute a command on
        cmd (str): The command string

    Returns:
        bool: True if succesful, False otherwise
    """
    _node: models.Node = db.pickle_to_model(node)
    cmd_opts = [
        "-i",
        str(_node.layout.ssh_private_key),
        f"{_node.layout.username}@{_node.public_ip}",
    ]
    cmd_opts.append(cmd)
    error_code = 0
    try:
        out = sh.ssh(cmd_opts, _env=state.app.env, _err_to_out=True)  # type: ignore
        _node.actions.append(
            models.Actions(
                exit_code=out.exit_code,
                out=out.stdout.decode(),
                error=out.stderr.decode(),
            )
        )
    except sh.ErrorReturnCode as e:
        error_code = e.exit_code  # type: ignore
        _node.actions.append(
            models.Actions(
                exit_code=e.exit_code,  # type: ignore
                out=e.stdout.decode(),
                error=e.stderr.decode(),
            )
        )
    db.M.save(_node.instance_name, _node)
    return bool(error_code == 0)


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

    rows: list[models.Node] = db.get_nodes().unwrap()
    if tag:
        rows = [node for node in rows if tag in node.layout.tags]
    elif name:
        rows = [node for node in rows if node.instance_name == name]
    count = len(rows)

    log.info(f"Executing '{cmd}' across {count} nodes.")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(exec, cmd=cmd)
        results = [executor.submit(func, db.model_as_pickle(node)) for node in rows]
        wait(results)
        return list(node.result() for node in results)


def exec_scripts(node: bytes, path: str) -> bytes:
    """Execute a scripts/template directory on a Node

    Function for executing scripts/templates on a node.

    **Synopsis:**

        from ogc import actions, state, db
        node = db.query(db.Node).first()
        result = actions.exec_scripts(node, "templates/deploy/ubuntu")
        result == True

    Args:
        node (bytes): The Pickled `models.Node` to execute scripts on
        path (str): The path where the scripts reside locally

    Returns:
        bytes: Pickled `models.Node` if succesful, False otherwise.
    """
    _node: models.Node = db.pickle_to_model(node)
    choose_provisioner(_node.layout.provider, _node.layout)
    deploy = Deployer(_node)
    return db.model_as_pickle(deploy.exec_scripts(path).unwrap())


def exec_scripts_async(
    path: str, filters: t.Mapping[str, str] | None = None
) -> list[models.Node]:
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
        list[models.Node]: `models.Node` if succesful, False otherwise.
    """
    rows: list[models.Node] = db.get_nodes().unwrap()
    if filters and "tag" in filters:
        rows = [
            node
            for node in rows
            if node.layout.tags and filters["tag"] in node.layout.tags
        ]
    elif filters and "name" in filters:
        rows = [node for node in rows if node.instance_name == filters["name"]]
    count = len(rows)
    log.info(f"Executing scripts from '{path}' across {count} nodes.")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(exec_scripts, path=path)
        results = [executor.submit(func, db.model_as_pickle(node)) for node in rows]
        wait(results)
        return [db.pickle_to_model(node.result()) for node in results]
