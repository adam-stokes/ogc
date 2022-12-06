"""signals"""

from __future__ import annotations

from blinker import signal

before_provision = signal("before-provision")
ready_provision = signal("ready-provision")
after_provision = signal("after-provision")


before_teardown = signal("before-teardown")
ready_teardown = signal("ready-teardown")
after_teardown = signal("after-teardown")
