import os
from pathlib import Path
from typing import Dict

import sh
from rich.console import Console

from ogc import db, enums, log, state

from .celery import app
from .deployer import Deployer
from .provision import choose_provisioner

console = Console()

@app.task
def do_provision(layout, env):
    console.log(f"Provisioning: {layout['name']}")
    engine = choose_provisioner(layout["provider"], env=env)
    engine.setup(layout["ssh_public_key"])
    model = engine.create(layout=layout, env=env)
    console.log(f"Saved {model.instance_name}")
    return model.id


@app.task
def end_provision(results):
    return results


@app.task
def do_deploy(node_id: int):
    session = db.connect()
    node = session.query(db.Node).filter(db.Node.id == node_id).one()
    session.close()

    console.log(f"Deploying to: {node.instance_name}")
    result = Deployer(node, state.app.env).run()
    result.show()
    return True


@app.task
def do_destroy(name: str, env: Dict[str, str], force: bool = False) -> None:
    session = db.connect()
    node_data = session.query(db.Node).filter(db.Node.instance_name == name).one()
    if node_data:
        uuid = node_data.uuid
        engine = choose_provisioner(node_data.provider, env=env)
        try:
            deploy = Deployer(node_data, env=state.app.env, force=force)

            # Pull down artifacts if set
            if node_data.artifacts:
                console.log("Downloading artifacts")
                local_artifact_path = (
                    Path(enums.LOCAL_ARTIFACT_PATH) / node_data.instance_name
                )
                if not local_artifact_path.exists():
                    os.makedirs(str(local_artifact_path), exist_ok=True)
                deploy.get(node_data.artifacts, str(local_artifact_path))

            exec_result = deploy.exec("./teardown")
            if not exec_result.passed:
                log.error(f"Unable to run teardown script on {node_data.instance_name}")
            console.log(f"Destroying {node_data.instance_name}")
            is_destroyed = deploy.node.destroy()
            if not is_destroyed:
                log.error(f"Unable to destroy {deploy.node.id}")

            ssh_deleted_err = engine.cleanup(node_data)
            if ssh_deleted_err:
                log.error(f"Could not delete ssh keypair {uuid}")
        except:
            log.error("Failed to delete node, removing from database.")
    session.delete(node_data)
    session.commit()
    session.close()


@app.task
def do_exec(
    cmd: str, ssh_private_key: str, node_id: int, username: str, public_ip: str
) -> bool:
    session = db.connect()
    node_data = session.query(db.Node).filter(db.Node.id == node_id).one()
    cmd_opts = ["-i", str(ssh_private_key), f"{username}@{public_ip}"]
    cmd_opts.append(cmd)
    try:
        out = sh.ssh(cmd_opts, _env=state.app.env, _err_to_out=True)
        result_obj = db.Actions(
            node=node_data,
            exit_code=out.exit_code,
            out=out.stdout.decode(),
            error=out.stderr.decode(),
        )
        session.add(result_obj)
        session.commit()
        session.close()
        return True
    except sh.ErrorReturnCode as e:
        result_obj = db.Actions(
            node=node_data,
            exit_code=e.exit_code,
            out=e.stdout.decode(),
            error=e.stderr.decode(),
        )
        session.add(result_obj)
        session.commit()
        session.close()
        return e.exit_code == 0


@app.task
def do_exec_scripts(node_id: int, path: str) -> bool:
    session = db.connect()
    node_data = session.query(db.Node).filter(db.Node.id == node_id).one()
    session.close()
    choose_provisioner(node_data.provider, env=state.app.env)
    deploy = Deployer(node_data, env=state.app.env)
    result = deploy.exec_scripts(path)
    result.save()
    return result.passed


@app.task
def end_exec(results):
    return results
