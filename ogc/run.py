import os
import tempfile
from pathlib import Path

import sh


def make_executable(path):
    mode = os.stat(str(path)).st_mode
    mode |= (mode & 0o444) >> 2
    os.chmod(str(path), mode)


def script(script_data, env, log, timeout=None, concurrent=False):
    # preserve color
    # script --flush \
    #        --quiet \
    #        --return /tmp/ansible-output.txt \
    #        --command "my-ansible-command"
    _run = sh.env
    if "sudo" in script_data:
        _run = sh.contrib.sudo.env
    if not script_data[:2] != "#!":
        script_data = "#!/bin/bash\n" + script_data
    tmp_script = tempfile.mkstemp()
    tmp_script_path = Path(tmp_script[-1])
    tmp_script_path.write_text(script_data, encoding="utf8")
    make_executable(tmp_script_path)
    os.close(tmp_script[0])
    if concurrent:
        cmd = _run(
            str(tmp_script_path), _env=env.copy(), _timeout=timeout, _bg=concurrent
        )
        cmd.wait()
    else:
        for line in _run(
            str(tmp_script_path),
            _env=env.copy(),
            _timeout=timeout,
            _iter=True,
            _bg_exc=False,
            _tty_in=True,
        ):
            log.info(line.strip())
    sh.rm("-rf", tmp_script_path)
