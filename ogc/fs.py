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
