""" application state module
"""
from types import SimpleNamespace


app = SimpleNamespace(
    # spec object
    spec=None,
    # debug
    debug=None,
    # plugins
    plugins=[],
)
