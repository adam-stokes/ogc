from __future__ import annotations

import os
import shutil
from pathlib import Path as Path_


def gcloud() -> str | None:
    """return path to gcloud"""
    return shutil.which("gcloud")


def ensure_cache_dir() -> Path_:
    """Make sure cache directory exists

    Returns:
        Path to cache_dir
    """
    cache_dir = Path(__file__).cwd() / ".ogc-cache"

    if not cache_dir.exists():
        os.makedirs(str(cache_dir))
    return cache_dir


def expand_path(p: str) -> Path_:
    """Returns expanded path

    Args:
        p: tilde path string to expand

    Returns:
        Path object expanded
    """
    return Path_(p).expanduser()


Path = Path_
