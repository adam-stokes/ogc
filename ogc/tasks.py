from typing import Dict

from ogc import db, log, state

from .celery import app
from .provision import Deployer, choose_provisioner


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
            node = engine.node(instance_id=node_data.instance_id)
            log.info(f"Destroying {node_data.instance_name}")
            is_destroyed = node.destroy()
            if not is_destroyed:
                log.error(f"Unable to destroy {node.id}")

            ssh_deleted_err = engine.cleanup(node_data)
            if ssh_deleted_err:
                log.error(f"Could not delete ssh keypair {uuid}")
        except:
            log.error("Failed to delete node, removing from database.")
    node_data.delete_instance()
