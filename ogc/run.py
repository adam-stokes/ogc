import os
import shlex
import subprocess
import tempfile
from pathlib import Path

import sh


def make_executable(path):
    mode = os.stat(str(path)).st_mode
    mode |= (mode & 0o444) >> 2
    os.chmod(str(path), mode)


def script(script_data, env, **kwargs):
    # preserve color
    # script --flush \
    #        --quiet \
    #        --return /tmp/ansible-output.txt \
    #        --command "my-ansible-command"
    is_single_command = len(script_data.splitlines()) == 1

    args = []
    if not is_single_command:
        if not script_data[:2] != "#!":
            script_data = "#!/bin/bash\n" + script_data
        tmp_script = tempfile.mkstemp()
        tmp_script_path = Path(tmp_script[-1])
        tmp_script_path.write_text(script_data, encoding="utf8")
        make_executable(tmp_script_path)
        os.close(tmp_script[0])
        args = ["bash", str(tmp_script_path)]
        subprocess.run(args, env=env.copy(), **kwargs)
        sh.rm("-rf", tmp_script_path)
    else:
        args = shlex.split(script_data.strip())
        subprocess.run(args, env=env.copy(), **kwargs)
