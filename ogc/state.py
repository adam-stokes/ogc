""" application state module
"""
import os
from types import SimpleNamespace

from melddict import MeldDict

from . import log
from .collect import Collector

app = SimpleNamespace(
    # spec object
    spec=None,
    # debug
    debug=None,
    # environment variables, these are accessible throughout all plugins
    env=MeldDict(os.environ.copy()),
    # list of all plugins, across all phases
    plugins=[],
    # logger
    log=log,
    # collector
    collect=Collector(),
    # jobs
    jobs=[],
)
