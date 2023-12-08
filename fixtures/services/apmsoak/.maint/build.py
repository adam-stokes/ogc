import shutil
import subprocess
import tempfile
from pathlib import Path

import structlog

script_path = Path(__file__).resolve().parent
log = structlog.get_logger()

with tempfile.TemporaryDirectory() as td:
    _dir = Path(td)
    _apm_server_path = _dir / "apm-server"
    log.info("Getting apm-server")
    subprocess.run(
        "git clone --depth=1 https://github.com/elastic/apm-server/",
        shell=True,
        check=True,
        cwd=_dir,
    )
    log.info(
        "remove dockerignore",
        path=_apm_server_path / ".dockerignore",
        exists=(_apm_server_path / ".dockerignore").exists(),
    )
    subprocess.run(
        "rm .dockerignore",
        cwd=_apm_server_path,
        shell=True,
        check=True,
    )
    log.info("Copy dockerfile to build env")
    shutil.copyfile(script_path / "Dockerfile", _apm_server_path / "Dockerfile")
    log.info("Build apmsoak")
    subprocess.run(
        "docker build -t docker.elastic.co/observability-ci/apmsoak:next .",
        shell=True,
        check=True,
        cwd=_apm_server_path,
    )
    log.info("Uploading apmsoak")
    subprocess.run(
        "docker push docker.elastic.co/observability-ci/apmsoak:next",
        shell=True,
        check=True,
        cwd=_apm_server_path,
    )
