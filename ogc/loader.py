"""module loader utils"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path


def from_path(path: Path) -> object | None:
    """Loads module into intepreter"""
    path_parents = path.parent
    sys.path.insert(0, str(path_parents.resolve()))
    module = path.parts[-1]
    modname, _ = os.path.splitext(module)
    try:
        return importlib.import_module(modname)
    except TypeError:
        return None
