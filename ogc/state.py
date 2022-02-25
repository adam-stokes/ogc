""" application state module
"""
import os
from types import SimpleNamespace

from dotenv import dotenv_values

from . import log

app = SimpleNamespace(
    # spec object
    spec=None,
    # Machine provisioning layouts from spec
    layouts=None,
    # environment variables, these are accessible throughout the provisioning
    env={**dotenv_values(".env"), **os.environ},
    # logger
    log=log,
    # run prefix
    prefix=None,
)
