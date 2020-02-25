""" application state module
"""
import os
import redis
from types import SimpleNamespace

from melddict import MeldDict

from . import log

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
    # jobs
    jobs=[],
    # redis
    redis=redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
)
