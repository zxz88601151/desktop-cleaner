"""Formatting helpers."""
from __future__ import annotations


def human_size(num: int) -> str:
    """Format a byte count into a human readable string (B / KB / MB / GB / TB)."""
    num = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024.0:
            if unit == "B":
                return f"{int(num)} {unit}"
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"
