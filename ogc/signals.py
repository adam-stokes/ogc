"""signals"""

from __future__ import annotations

from blinker import signal

before_provision = signal("before-provision")
ready_provision = signal("ready-provision")
after_provision = signal("after-provision")


before_teardown = signal("before-teardown")
ready_teardown = signal("ready-teardown")
after_teardown = signal("after-teardown")

init = signal("ogc-init")
up = signal("ogc-up")
down = signal("ogc-down")
run = signal("ogc-run")
ls = signal("ogc-ls")
exec = signal("ogc-exec")
exec_scripts = signal("ogc-exec-scripts")
put = signal("ogc-put")
get = signal("ogc-get")
ssh = signal("ogc-ssh")
