""" application state module
"""
from melddict import MeldDict
from types import SimpleNamespace
import os

app = SimpleNamespace(
    # spec object
    spec=None,
    # debug
    debug=None,
    # environment variables, these are accessible throughout all plugins
    env=MeldDict(os.environ.copy()),
    # plugins
    plugins=[],
    # logger
    log=None,
)
