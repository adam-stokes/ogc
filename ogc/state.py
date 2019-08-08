""" application state module
"""
from .enums import SPEC_PHASES
from melddict import MeldDict
from types import SimpleNamespace
from collections import OrderedDict
import os

app = SimpleNamespace(
    # spec object
    spec=None,
    # debug
    debug=None,
    # environment variables, these are accessible throughout all plugins
    env=MeldDict(os.environ.copy()),
    # phases
    phases=OrderedDict([(phase, []) for phase in SPEC_PHASES]),
    # list of all plugins, across all phases
    plugins=[],
    # logger
    log=None,
)
