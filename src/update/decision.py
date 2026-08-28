"""Update decision logic — pure, no Qt, no network.

Maps (current_version, manifest) to one of four levels:
- NONE      : current >= latest (up to date, or newer than latest)
- NORMAL    : a patch-level bump (e.g. 1.1.0 -> 1.1.1)
- IMPORTANT : a minor/major bump (e.g. 1.1.0 -> 1.2.0)
- FORCE     : current < minimum_supported_version (must update, no "later")
"""
from __future__ import annotations

from .version import is_newer, is_older_than, parse_version

LEVEL_NONE = "none"
LEVEL_NORMAL = "normal"
LEVEL_IMPORTANT = "important"
LEVEL_FORCE = "force"


def evaluate(current_version: str, manifest: dict) -> str:
    """Return the update level for the running `current_version` against `manifest`."""
    minimum = manifest.get("minimum_supported_version")
    if minimum and is_older_than(minimum, current_version):
        return LEVEL_FORCE

    if not is_newer(manifest["latest_version"], current_version):
        return LEVEL_NONE

    cur = parse_version(current_version)
    lat = parse_version(manifest["latest_version"])
    if lat[0] > cur[0] or lat[1] > cur[1]:
        return LEVEL_IMPORTANT
    return LEVEL_NORMAL
