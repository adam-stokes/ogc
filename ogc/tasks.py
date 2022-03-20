from ogc import log
from ogc.cache import Cache

from .celery import app
from .provision import Deployer, choose_provisioner


@app.task
def do_provision(layout, env):
    log.info(f"Provisioning: {layout.name}")
    engine = choose_provisioner(layout.provider, env=env)
    engine.setup(layout)
    return engine.create(layout=layout, env=env)


@app.task
def end_provision(results):
    return results


@app.task
def do_deploy(provision_result, metadata, msg_cb):
    log.info(f"Deploying: {provision_result}")
    result = Deployer(provision_result)
    return result.run(metadata, msg_cb)


@app.task
def end_deploy(results):
    return results


@app.task
def do_destroy(name, env):
    cache_obj = Cache()
    node_data = None
    if not cache_obj.exists(name):
        log.error(f"Unable to find {layout.name} in cache")
    node_data = cache_obj.load(name)
    if node_data:
        uuid = node_data.id
        node = node_data.node
        layout = node_data.layout
        engine = choose_provisioner(layout.provider, env=env)
        node = engine.node(instance_id=node.id)
        log.info(f"Destroying {layout.name}")
        is_destroyed = node.destroy()
        if not is_destroyed:
            log.error(f"Unable to destroy {node.id}")

        ssh_deleted_err = engine.cleanup(node_data)
        if ssh_deleted_err:
            log.error(f"Could not delete ssh keypair {uuid}")
    cache_obj.delete(name)
