"""Path helpers — Windows long-path safety, cross-platform passthrough.

SQLite / ``shutil`` / ``os.path`` calls on Windows silently fail for paths
longer than ~260 characters unless the ``\\?\\`` namespace prefix is used.
We only add the prefix when a path is actually long, so normal paths keep
their familiar form and other APIs behave identically.
"""
from __future__ import annotations

import os


def win_long(p) -> str:
    """Return an OS path string that survives >260-char limits on Windows.

    - Non-Windows: straight passthrough (``str(p)``).
    - Windows: prefix with ``\\\\?\\`` only when the absolute path is long
      (>= 240 chars), leaving short paths untouched to avoid surprises.
    """
    if os.name != "nt":
        return str(p)
    s = str(p)
    if s.startswith("\\\\?\\"):
        return s
    ap = os.path.abspath(s)
    if len(ap) >= 240:
        return "\\\\?\\" + ap
    return ap


def safe_exists(p) -> bool:
    try:
        return os.path.exists(win_long(p))
    except OSError:
        return False


def safe_is_file(p) -> bool:
    try:
        return os.path.isfile(win_long(p))
    except OSError:
        return False
