"""Version parsing / comparison — pure, no Qt, no network.

Uses true semantic-version comparison so that, e.g., "1.1.9" < "1.1.10"
(numeric tuple compare, never lexicographic string compare).
"""
from __future__ import annotations

import re

_VERSION_RE = re.compile(r"^\s*(\d+)\.(\d+)\.(\d+)\s*$")


def parse_version(v: str):
    """Return (major, minor, patch) as ints, or raise ValueError if malformed."""
    m = _VERSION_RE.match(v or "")
    if not m:
        raise ValueError(f"invalid version string: {v!r}")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def compare_versions(a: str, b: str) -> int:
    """Return -1 if a<b, 0 if equal, 1 if a>b (numeric, not lexical)."""
    pa, pb = parse_version(a), parse_version(b)
    return (pa > pb) - (pa < pb)


def is_newer(latest: str, current: str) -> bool:
    """True if `latest` is strictly greater than `current`."""
    return compare_versions(latest, current) > 0


def is_older_than(minimum: str, current: str) -> bool:
    """True if `current` is strictly less than `minimum` (force-update case)."""
    return compare_versions(current, minimum) < 0
