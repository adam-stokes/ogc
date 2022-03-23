from typing import Dict

import sh

from ogc import db, log, state

from .celery import app
from .deployer import Deployer
from .provision import choose_provisioner


@app.task
def do_provision(layout, env):
    log.info(f"Provisioning: {layout['name']}")
    engine = choose_provisioner(layout["provider"], env=env)
    engine.setup(layout["ssh_public_key"])
    model = engine.create(layout=layout, env=env)
    log.info(f"Saved {model.instance_name}")
    return model.id


@app.task
def end_provision(results):
    return results


@app.task
def do_deploy(node_id: int):
    node = db.NodeModel.get(db.NodeModel.id == node_id)

    log.info(f"Deploying to: {node.instance_name}")
    result = Deployer(node, state.app.env).run()
    result.show()
    return True


@app.task
def do_destroy(name: str, env: Dict[str, str]) -> None:
    node_data = db.NodeModel.get(db.NodeModel.instance_name == name)
    if node_data:
        uuid = node_data.uuid
        engine = choose_provisioner(node_data.provider, env=env)
        try:
            deploy = Deployer(node_data, state.app.env)
            exec_result = deploy.exec("./teardown")
            if not exec_result.passed:
                log.error(f"Unable to run teardown script on {node_data.instance_name}")
            log.info(f"Destroying {node_data.instance_name}")
            is_destroyed = deploy.node.destroy()
            if not is_destroyed:
                log.error(f"Unable to destroy {deploy.node.id}")

            ssh_deleted_err = engine.cleanup(node_data)
            if ssh_deleted_err:
                log.error(f"Could not delete ssh keypair {uuid}")
        except:
            log.error("Failed to delete node, removing from database.")
    node_data.delete_instance()


@app.task
def do_exec(
    cmd: str, ssh_private_key: str, node_id: int, username: str, public_ip: str
) -> None:
    node_data = db.NodeModel.get(db.NodeModel.id == node_id)
    cmd_opts = ["-i", str(ssh_private_key), f"{username}@{public_ip}"]
    cmd_opts.append(cmd)
    out = sh.ssh(cmd_opts, _env=state.app.env, _err_to_out=True)
    db.NodeActionResult.create(
        node=node_data,
        exit_code=out.exit_code,
        out=out.stdout.decode(),
        err=out.stderr.decode(),
    )
    return out.exit_code == 0


@app.task
def end_exec(results):
    return results
