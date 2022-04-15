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

from ogc import db, enums, models, state
from ogc.deployer import Deployer
from ogc.log import Logger as log
from ogc.provision import choose_provisioner

# Not advertised, but available for those who seek moar power.
MAX_WORKERS = int(os.environ.get("OGC_MAX_WORKERS", cpu_count() - 1))


def launch(layout: bytes, config: bytes) -> bytes:
    """Launch a node.

    Synchronous function for launching a node in a cloud environment.

    **Synopsis:**

        from ogc.spec import SpecLoader
        from ogc import actions

        config.spec = SpecLoader.load(["/Users/adam/specs/ogc.yml"])
        node_ids_created = [actions.launch(layout.as_dict())
                            for layout in config.spec.layouts]

    Args:
        layout (bytes): The layout specification used
            when launching a node.
        config (bytes): Configuration model

    Returns:
        bytes: Pickled Instance if successful, None otherwise.
    """
    _layout: models.Layout = db.pickle_to_model(layout)
    _config: models.User = db.pickle_to_model(config)

    log.info(f"Provisioning: {_layout.name}")
    engine = choose_provisioner(name=_layout.provider, layout=_layout, config=_config)
    engine.setup()
    model = engine.create()
    return db.model_as_pickle(model)


def launch_async(
    layouts: list[models.Layout], config: models.User
) -> list[models.Node]:
    """Launch a node asynchronously.

    Asynchronous function for launching a node in a cloud environment.

    **Synopsis:**

        from ogc.spec import SpecLoader
        from ogc import actions, db, models

        user = db.get_user().unwrap()
        user.spec = SpecLoader.load(["/Users/adam/specs/ogc.yml"])
        node_ids_created = actions.launch_async(layouts=user.spec.layouts, config=user)

    Args:
        layouts (list[models.Layout]): The layout specification used
            when launching a node.
        config (models.User): Application config object

    Returns:
        List[models.Node]: List of launched node instances
    """

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(launch, config=db.model_as_pickle(config))
        results = executor.map(
            func,
            [
                db.model_as_pickle(layout)
                for layout in layouts
                for _ in range(layout.scale)
            ],
        )
        return [db.pickle_to_model(layout) for layout in results]


def deploy(node: bytes, config: bytes) -> bytes:
    """Execute the deployment

    Function for executing the deployment on a node.

    **Synopsis:**

        from ogc.spec import SpecLoader
        from ogc import actions, db, models

        user = db.get_user().unwrap()
        user.spec = SpecLoader.load(["/Users/adam/specs/ogc.yml"])
        name = actions.deploy(db.model_as_pickle(user.nodes[0]))

    Args:
        node (bytes): Picked `models.Node` object
        config (bytes): Pickled `models.User` object

    Returns:
        bytes: Pickled `models.Node` deployed to, Error otherwise.
    """
    _node: models.Node = db.pickle_to_model(node)
    _config: models.User = db.pickle_to_model(config)
    log.info(f"Deploying to: {_node.instance_name}")
    dep = Deployer(_node, _config).run()
    if dep.ok():
        return db.model_as_pickle(_node)
    return Err(f"Failed to deploy: {dep}").unwrap()


def deploy_async(nodes: list[models.Node], config: models.User) -> list[models.Node]:
    """Execute the deployment

    Asynchronous function for executing the deployment on a node.

    **Synopsis:**

        from ogc.spec import SpecLoader
        from ogc import actions, db, models
        from attr import asdict

        user = db.get_user().unwrap()
        user.spec = SpecLoader.load(["/Users/adam/specs/ogc.yml"])
        names = actions.deploy_async(user.nodes)

    Args:
        nodes (list[models.Node]): The nodes to deploy to

    Returns:
        list[models.Node]: A list of nodes deployed.
    """
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(deploy, config=db.model_as_pickle(config))
        results = executor.map(
            func,
            [db.model_as_pickle(node) for node in nodes],
        )
        return [db.pickle_to_model(node) for node in results]


def teardown(
    node: bytes,
    config: bytes,
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
        config (bytes): Pickled `models.User`
        force (bool): Force
        only_db (bool): Will remove from database regardless of cloud state. Use with
            caution.

    Returns:
        bytes: Pickled `models.Node` that was removed, None otherwise.
    """
    _node: models.Node = db.pickle_to_model(node)
    _config: models.User = db.pickle_to_model(config)

    log.info(f"Destroying: {_node.instance_name}")
    if not only_db:
        deploy = Deployer(_node, config=_config, force=force)
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

            exec_result = deploy.exec("./teardown")
            if not exec_result.ok():
                log.error(f"Unable to run teardown script on {_node.instance_name}")
        is_destroyed = deploy.node.destroy()
        if not is_destroyed:
            log.critical(f"Unable to destroy {_node.instance_id}")

    return node


def teardown_async(
    nodes: list[models.Node],
    config: models.User,
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
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        func = partial(
            teardown, config=db.model_as_pickle(config), only_db=only_db, force=force
        )
        results = executor.map(func, [db.model_as_pickle(node) for node in nodes])
        return [db.pickle_to_model(node) for node in results]


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


def exec_scripts(node: models.Node, path: str) -> bool:
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
