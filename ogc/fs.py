from __future__ import annotations

import os
from pathlib import Path as Path_


def ensure_cache_dir() -> Path_:
    """Make sure cache directory exists"""
    cache_dir = Path(__file__).cwd() / ".ogc-cache"

    if not cache_dir.exists():
        os.makedirs(str(cache_dir))
    return cache_dir


def expand_path(p: str) -> Path_:
    """Returns expanded path"""
    return Path_(p).expanduser()


Path = Path_
