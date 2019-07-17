""" application state module
"""
from types import SimpleNamespace
import os

app = SimpleNamespace(
    # spec object
    spec=None,
    # debug
    debug=None,

    # environment variables, these are accessible throughout all plugins
    env=os.environ.copy(),

    # plugins
    plugins=[],
)
