"""Scan a directory and produce a preview of files grouped by category."""
from __future__ import annotations

import datetime
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .classifier import classify
from .rules import (
    DEFAULT_RULES,
    CATEGORY_NAMES,
    category_display,
    get_exclude_dirs,
    is_date_dir,
)
from utils.paths import win_long
from utils.logger import get_logger

_log = get_logger("scanner")


# Windows shell / system files that must never be moved.
_SYSTEM_FILES = {"desktop.ini", "thumbs.db", "ehthumbs.db"}

# FILE_ATTRIBUTE_HIDDEN on Windows
_HIDDEN_ATTR = 0x2


def _is_hidden(path: Path) -> bool:
    """Return True for hidden files (best-effort, cross-platform)."""
    if os.name == "nt":
        try:
            import ctypes

            # P1-5: use the long-path-safe form so hidden detection works on
            # deeply nested paths too.
            attrs = ctypes.windll.kernel32.GetFileAttributesW(win_long(path))
            if attrs == -1:
                return False
            return bool(attrs & _HIDDEN_ATTR)
        except Exception:  # noqa: BLE001 - cannot determine -> treat as visible
            return False
    return path.name.startswith(".")


@dataclass
class ScanResult:
    root: Path
    files: List[Path] = field(default_factory=list)
    by_category: Dict[str, int] = field(default_factory=dict)
    by_category_size: Dict[str, int] = field(default_factory=dict)
    total_size: int = 0

    @property
    def total(self) -> int:
        return len(self.files)


def _date_label(path: Path) -> str:
    try:
        ts = path.stat().st_mtime
    except OSError:
        ts = datetime.datetime.now().timestamp()
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m")


def scan(
    root: Path,
    mode: str = "type",
    recursive: bool = False,
    rules: Optional[Dict[str, str]] = None,
    exclude_dirs: Optional[set] = None,
) -> ScanResult:
    """Scan *root* and group files.

    - ``mode="type"`` groups by file category (图片 / 文档 / ...).
    - ``mode="date"`` groups by modification month (2026-08 ...).

    Already-organized folders are skipped so a second run does not move
    files that were already sorted.
    """
    rules = rules or DEFAULT_RULES
    if exclude_dirs is None:
        exclude_dirs = get_exclude_dirs(mode)

    # P0-4: never allow organizing the app's own data directory (holds the DB).
    from data.database import data_dir

    if Path(root).resolve() == data_dir().resolve():
        raise ValueError(
            "不能整理应用自身的数据目录（包含数据库文件），请选择其他文件夹。"
        )

    # P1-3: always skip output folders produced by *either* mode, regardless of
    # the current mode. This prevents a folder already sorted by type (e.g.
    # "图片") from being re-processed when the user later runs date mode (and
    # vice versa for "2026-08"). A real file therefore yields at most one plan
    # item per scan round.
    _ALWAYS_SKIP = set(CATEGORY_NAMES.values())

    _log.info(
        "SCAN START root=%s mode=%s recursive=%s", root, mode, recursive
    )

    result = ScanResult(root=Path(root))
    candidates: List[Path] = []

    iterator = root.rglob("*") if recursive else root.glob("*")
    for entry in iterator:
        if not entry.is_file():
            continue
        # P0-4: skip Windows system files & hidden files.
        if entry.name.lower() in _SYSTEM_FILES:
            continue
        if _is_hidden(entry):
            continue
        # Skip output folders from previous runs (both modes).
        rel = entry.relative_to(root)
        parts = rel.parts
        if parts and (parts[0] in _ALWAYS_SKIP or parts[0] in exclude_dirs
                      or is_date_dir(parts[0])):
            continue
        candidates.append(entry)

    for f in candidates:
        if mode == "date":
            label = _date_label(f)
        else:
            label = category_display(classify(f, rules))
        result.files.append(f)
        result.by_category[label] = result.by_category.get(label, 0) + 1
        try:
            size = f.stat().st_size
        except OSError:
            size = 0
        result.by_category_size[label] = result.by_category_size.get(label, 0) + size
        result.total_size += size

    _log.info(
        "SCAN DONE root=%s files=%d categories=%d total_bytes=%d",
        root, result.total, len(result.by_category), result.total_size,
    )
    return result
