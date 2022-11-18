from __future__ import annotations

import os
from pathlib import Path
from typing import List


def walk(src: Path, excludes: List[str] = []) -> List[Path]:
    if not isinstance(src, Path):
        src = Path(src)

    includes = []
    for p in src.rglob("*"):
        # TODO: make this check better
        if not any(exclude in str(p) for exclude in excludes):
            includes.append(p)
    return includes


def ensure_cache_dir() -> Path:
    """Make sure cache directory exists"""
    cache_dir = Path(__file__).cwd() / ".ogc-cache"

    if not cache_dir.exists():
        os.makedirs(str(cache_dir))
    return cache_dir
