from __future__ import annotations

import os
from pathlib import Path


def ensure_cache_dir() -> Path:
    """Make sure cache directory exists"""
    cache_dir = Path(__file__).cwd() / ".ogc-cache"

    if not cache_dir.exists():
        os.makedirs(str(cache_dir))
    return cache_dir
