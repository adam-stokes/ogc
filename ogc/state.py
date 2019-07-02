""" application state module
"""
from types import SimpleNamespace


class StateConfig:
    """ Application state
    """

    # Config object
    config = None

    # debug
    debug = None


app = StateConfig()
