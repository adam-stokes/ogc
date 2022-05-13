import os
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count
from pathlib import Path

import sh
from pampy import match
from safetywrap import Err
from toolz.curried import filter
from toolz.functoolz import partial, thread_last

from ogc import db, enums, models, state
from ogc.deployer import Deployer
from ogc.log import Logger as log
from ogc.provision import choose_provisioner
from ogc.spec import CountCtx

# Not advertised, but available for those who seek moar power.
MAX_WORKERS = int(os.environ.get("OGC_MAX_WORKERS", cpu_count() - 1))


def launch(layout: bytes, user: bytes) -> bytes:
    """Launch a node.

    Synchronous function for launching a node in a cloud environment.

    **Synopsis:**

        from ogc.spec import SpecLoader
        from ogc import actions, db

        usr = db.get_user().unwrap()
        spec = SpecLoader.load(["/Users/adam/specs/ogc.toml"])
        nodes = [actions.launch(layout)
                 for layout in spec.layouts]

    Args:
        layout (bytes): `models.Layout` specification used
            when launching a node.
        user (bytes): `models.User` model

    Returns:
        bytes: Pickled `models.Node` Instance if successful, None otherwise.
    """
    _layout: models.Layout = db.pickle_to_model(layout)
    _user: models.User = db.pickle_to_model(user)

    log.info(f"Provisioning: {_layout.name}")
    engine = choose_provisioner(name=_layout.provider, layout=_layout, user=_user)
    engine.setup()
    model = engine.create()
    return db.model_as_pickle(model)


def launch_async(layouts: list[models.Layout], user: models.User) -> list[models.Node]:
    """Launch a node asynchronously.

    Asynchronous function for launching a node in a cloud environment.

    **Synopsis:**

        from ogc.spec import SpecLoader
        from ogc import actions, db, models

        user = db.get_user().unwrap()
        user.spec = SpecLoader.load(["/Users/adam/specs/ogc.toml"])
        nodes = actions.launch_async(layouts=user.spec.layouts, config=user)

    Args:
        layouts (list[models.Layout]): The layout specification used
            when launching a node.
        user (models.User): `models.User` Application user object

    Returns:
        list[models.Node]: List of launched node instances
    """

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(launch, user=db.model_as_pickle(user))
        results = executor.map(
            func,
            [
                db.model_as_pickle(layout)
                for layout in layouts
                for _ in range(layout.scale)
            ],
        )
        for node in results:
            db.M.save(node.instance_name, node)
        return [db.pickle_to_model(node) for node in results]


def deploy(node: bytes) -> bytes:
    """Execute the deployment

    Function for executing the deployment on a node.

    **Synopsis:**

        from ogc.spec import SpecLoader
        from ogc import actions, db, models

        node = db.get_node('ogc-abc-node-name')
        actions.deploy(db.model_as_pickle(node))

    Args:
        node (bytes): Picked `models.Node` object

    Returns:
        bytes: Pickled `models.DeployResult` deployed to, Error otherwise.
    """
    _node: models.Node = db.pickle_to_model(node)
    log.info(f"Deploying to: {_node.instance_name}")
    dep = Deployer(_node).run().unwrap()
    if dep:
        return db.model_as_pickle(dep)
    return Err(f"Failed to deploy: {dep}").unwrap()


def deploy_async(nodes: list[models.Node]) -> list[models.Node]:
    """Execute the deployment

    Asynchronous function for executing the deployment on a node.

    **Synopsis:**

        from ogc.spec import SpecLoader
        from ogc import actions, db, models

        nodes = db.get_nodes()
        names = actions.deploy_async(nodes)

    Args:
        nodes (list[models.Node]): The nodes to deploy to

    Returns:
        list[models.Node]: A list of node deployed results.
    """
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(
            deploy,
            [db.model_as_pickle(node) for node in nodes],
        )
        return [db.pickle_to_model(node) for node in results]


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
                if not local_artifact_path.exists():
                    os.makedirs(str(local_artifact_path), exist_ok=True)
                deploy.get(_node.layout.artifacts, str(local_artifact_path))

            if not deploy.exec("./teardown").ok():
                log.error(f"Unable to run teardown script on {_node.instance_name}")
        is_destroyed = deploy.node.destroy()
        if not is_destroyed:
            log.critical(f"Unable to destroy {_node.instance_id}")

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
        user = db.get_user().unwrap_or_else(log.fatal)
        if not user:
            sys.exit(1)

        result = actions.teardown_async(user.nodes, force=True)
        assert(result == True)

    Args:
        nodes (list[models.Node]): The node name to teardown
        config (models.User): configuration object
        force (bool): Force
        only_db (bool): Will remove from database regardless of cloud state. Use with
            caution.

    Returns:
        list[models.Node]: List of nodes removed, empty otherwise
    """
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(teardown, only_db=only_db, force=force)
        results = executor.map(func, [db.model_as_pickle(node) for node in nodes])
        return [db.pickle_to_model(node) for node in results]


def sync(layout: bytes, user: bytes, overrides: dict[str, CountCtx]) -> bytes:
    """Sync a deployment

    Function for syncing a deployment to correct scale.

    **Synopsis:**

        from ogc import actions, state
        layout = app.spec.layouts[0]
        result = actions.sync(layout, overrides={'elastic-agent-ubuntu': {'action': 'add', remaining: 5}})
        result == True

    Args:
        layout (bytes): The Pickled `models.Layout`
        user (bytes): The Pickled `models.User`
        overrides (dict[str, str]): Override dictionary of what the new count of nodes should be

    Returns:
        bytes: True if synced, False otherwise
    """
    _layout: models.Layout = db.pickle_to_model(layout)
    override = overrides[_layout.name]

    def _sync_add() -> bytes:
        log.info(f"Adding deployments for {_layout.name}")
        func = partial(launch, user=user)
        return thread_last(layout, func, lambda x: x, deploy)

    def _sync_remove() -> bytes:
        log.info(f"Removing deployments for {_layout.name}")
        func = partial(teardown, force=True)
        return thread_last(
            db.get_nodes().unwrap(),
            filter(lambda x: x.instance_name.endswith(_layout.name)),
            list,
            lambda x: x[0],
            db.model_as_pickle,
            func,
        )

    return match(
        override,
        {"action": "add"},
        lambda x: _sync_add(),
        {"action": "remove"},
        lambda x: _sync_remove(),
    )


def sync_async(
    layouts: list[models.Layout], user: models.User, overrides: dict[str, CountCtx]
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
        func = partial(sync, user=db.model_as_pickle(user), overrides=overrides)
        results = executor.map(
            func,
            [
                db.model_as_pickle(layout)
                for layout in layouts
                for _ in range(abs(overrides[layout.name]["remaining"]))
            ],
        )
        return [db.pickle_to_model(node) for node in results]


def exec(node: bytes, cmd: str) -> bool:
    """Execute command on Node

    Function for executing a command on a node.

    **Synopsis:**

        from ogc import actions, state, db
        node = db.query(db.Node).first()
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
    assert _node.actions
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
        error_code = e.exit_code
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
        results = executor.map(
            func,
            [db.model_as_pickle(node) for node in rows],
        )
    return list(results)


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
        bytes: Pickled `models.DeployResult` if succesful, False otherwise.
    """
    _node: models.Node = db.pickle_to_model(node)
    choose_provisioner(_node.layout.provider, _node.layout, _node.user)
    deploy = Deployer(_node)
    return db.model_as_pickle(deploy.exec_scripts(path).unwrap())


def exec_scripts_async(name: str, tag: str, path: str) -> list[models.DeployResult]:
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
        list[models.DeployResult]: `models.DeployResult` if succesful, False otherwise.
    """
    rows: list[models.Node] = db.get_nodes().unwrap()
    if tag:
        rows = [node for node in rows if tag in node.layout.tags]
    elif name:
        rows = [node for node in rows if node.instance_name == name]
    count = len(rows)

    log.info("Executing scripts from '%s' across {%s} nodes." % path, count)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(exec_scripts, path=path)
        results = executor.map(
            func,
            [db.model_as_pickle(node) for node in rows],
        )
    return [db.pickle_to_model(model) for model in results]
