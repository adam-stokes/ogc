import os
import subprocess
import tempfile
from pathlib import Path

from .exceptions import SpecProcessException
from .state import app


def make_executable(path):
    mode = os.stat(str(path)).st_mode
    mode |= (mode & 0o444) >> 2
    os.chmod(str(path), mode)


def _log_sub_out(pipe):
    """ Logs output from subprocess
    """
    for line in iter(pipe.readline, b""):
        app.log.info(line.decode().strip())


def script(script_data, env, **kwargs):
    # preserve color
    # script --flush \
    #        --quiet \
    #        --return /tmp/ansible-output.txt \
    #        --command "my-ansible-command"
    is_single_command = len(script_data.splitlines()) == 1
    process = None
    if is_single_command:
        process = subprocess.Popen(
            script_data.strip(),
            shell=True,
            env=env.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            **kwargs
        )

    if not script_data[:2] != "#!":
        script_data = "#!/bin/bash\n" + script_data
    tmp_script = tempfile.mkstemp()
    tmp_script_path = Path(tmp_script[-1])
    tmp_script_path.write_text(script_data, encoding="utf8")
    make_executable(tmp_script_path)
    os.close(tmp_script[0])
    process = subprocess.Popen(
        ["bash", str(tmp_script_path)],
        env=env.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        **kwargs
    )
    with process.stdout:
        _log_sub_out(process.stdout)
    exitcode = process.wait()
    subprocess.run(["rm", "-rf", str(tmp_script_path)])
    if exitcode > 0:
        raise SpecProcessException("Failed to run script")
