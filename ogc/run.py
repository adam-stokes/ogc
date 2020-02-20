import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

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
        app.log.debug(line.decode().strip())


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


def capture(_script, **kwargs):
    """ capture command output
    """
    env = app.env.copy()
    if not isinstance(_script, list) and "shell" not in kwargs:
        _script = shlex.split(_script)
    process = subprocess.run(
        _script, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, **kwargs
    )
    return SimpleNamespace(
        ok=bool(process.returncode == 0),
        returncode=process.returncode,
        stdout=process.stdout,
        stderr=process.stderr,
    )


def cmd_ok(_script, **kwargs):
    """ Stream command, doesnt buffer and prints it all out to stdout, only
    returns exit status
    """
    env = app.env.copy()
    check = None
    if "check" in kwargs:
        check = kwargs["check"]
        del kwargs["check"]
    if not isinstance(_script, list) and "shell" not in kwargs:
        _script = shlex.split(_script)
    process = subprocess.Popen(
        _script, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, **kwargs
    )

    with process.stdout:
        _log_sub_out(process.stdout)
    exitcode = process.wait()
    if check and exitcode > 0:
        raise subprocess.CalledProcessError(exitcode, "", "")
    return SimpleNamespace(ok=bool(exitcode == 0), returncode=exitcode)
