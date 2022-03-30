import os
from pathlib import Path
from typing import Dict

import sh

from ogc import db, enums, state
from ogc.log import Logger as log

from .celery import app
from .deployer import Deployer
from .provision import choose_provisioner

if not state.app.engine:
    state.app.engine = db.connect()
    state.app.session = db.session(state.app.engine)

@app.task
def do_provision(layout: Dict[str, str]) -> int:
    log.info(f"Provisioning: {layout['name']}")
    engine = choose_provisioner(layout["provider"], env=state.app.env)
    engine.setup(layout)
    model = engine.create(layout=layout, env=state.app.env)
    log.debug(f"Saved {model.instance_name} to database")
    return model.id


@app.task
def end_provision(results):
    return results


@app.task
def do_deploy(node_id: int):
    with state.app.session as session:
        node = session.query(db.Node).filter(db.Node.id == node_id).one()

    log.info(f"Deploying to: {node.instance_name}")
    result = Deployer(node, state.app.env).run()
    result.show()
    return True


@app.task
def do_destroy(name: str, force: bool = False, only_db: bool = False) -> None:
    with state.app.session as session:
        node_data = session.query(db.Node).filter(db.Node.instance_name == name).first() or None
        if node_data and not only_db:
            try:
                engine = choose_provisioner(node_data.provider, env=state.app.env)

                deploy = Deployer(node_data, env=state.app.env, force=force)

                if not force:
                    # Pull down artifacts if set
                    if node_data.artifacts:
                        log.info("Downloading artifacts")
                        local_artifact_path = (
                            Path(enums.LOCAL_ARTIFACT_PATH) / node_data.instance_name
                        )
                        if not local_artifact_path.exists():
                            os.makedirs(str(local_artifact_path), exist_ok=True)
                        deploy.get(node_data.artifacts, str(local_artifact_path))

                    exec_result = deploy.exec("./teardown")
                    if not exec_result.passed:
                        log.error(f"Unable to run teardown script on {node_data.instance_name}")
                log.info(f"Destroying {node_data.instance_name}")
                is_destroyed = deploy.node.destroy()
                if not is_destroyed:
                    log.error(f"Unable to destroy {deploy.node.id}")
            except:
                log.warning(f"Couldn't destroy {node_data.instance_name}")
            engine.cleanup(node_data)
        session.delete(node_data)
        session.commit()


@app.task
def do_exec(
    cmd: str, ssh_private_key: str, node_id: int, username: str, public_ip: str
) -> bool:
    result = None
    with state.app.session as session:
        node_data = session.query(db.Node).filter(db.Node.id == node_id).one()
        cmd_opts = ["-i", str(ssh_private_key), f"{username}@{public_ip}"]
        cmd_opts.append(cmd)
        try:
            out = sh.ssh(cmd_opts, _env=state.app.env, _err_to_out=True)
            result = db.Actions(
                node=node_data,
                exit_code=out.exit_code,
                out=out.stdout.decode(),
                error=out.stderr.decode(),
            )
        except sh.ErrorReturnCode as e:
            result = db.Actions(
                node=node_data,
                exit_code=e.exit_code,
                out=e.stdout.decode(),
                error=e.stderr.decode(),
            )
        session.add(result)
        session.commit()
        return result.exit_code == 0


@app.task
def do_exec_scripts(node_id: int, path: str) -> bool:
    with state.app.session as session:
        node_data = session.query(db.Node).filter(db.Node.id == node_id).one()
        choose_provisioner(node_data.provider, env=state.app.env)
        deploy = Deployer(node_data, env=state.app.env)
        result = deploy.exec_scripts(path)
        result.save()
        return result.passed


@app.task
def end_exec(results):
    return results
