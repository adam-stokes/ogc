"""ogc template tag helpers"""

from __future__ import annotations

import sh

LINE_SEP = "-"


def run(exe: str, *args: str | None, **kwargs: bool | None) -> str:
    """Converts a `sh.Command` to it's string reprsentation"""
    cmd = sh.Command(exe)
    kwargs_parsed = {k: v for k, v in kwargs.items() if not k.startswith("_ogc")}
    out = str(cmd.bake(*args, **kwargs_parsed))
    return out


def header(msg: str) -> str:
    """Prints header string"""
    out = [hr(), f"echo {msg}", hr()]
    return "\n".join(out)


def hr() -> str:
    """Prints seperator"""
    return f"echo {LINE_SEP * 79}"
