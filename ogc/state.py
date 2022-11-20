""" application state module
"""
from __future__ import annotations

import os
from types import SimpleNamespace

from dotenv import dotenv_values

from ogc.log import get_logger

log = get_logger(__name__)


def load_env():
    """Loads environment variables"""
    return {**dotenv_values(".env"), **os.environ}


app = SimpleNamespace(
    # spec object
    spec=None,
    # Machine provisioning layouts from spec
    layouts=None,
    # environment variables, these are accessible throughout the provisioning
    env=load_env(),
    # logger
    log=log,
    # db engine
    engine=None,
    # session
    session=None,
)
