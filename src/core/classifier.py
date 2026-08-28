"""Classify a single file path into a category key."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from .rules import DEFAULT_RULES


def classify(path: Path, rules: Optional[Dict[str, str]] = None) -> str:
    """Return the category key for *path*.

    Unknown extensions fall back to ``others``.
    """
    rules = rules or DEFAULT_RULES
    ext = path.suffix.lower().lstrip(".")
    return rules.get(ext, "others")
