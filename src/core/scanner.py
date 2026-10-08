"""Scan a directory and produce a preview of files grouped by category."""
from __future__ import annotations

import datetime
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

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
    """Return True for hidden files (best-effort, cross-platform).

    Kept as the canonical path-based check for callers that only have a
    :class:`Path` (e.g. empty-folder detection). The hot path in :func:`scan`
    uses :func:`_entry_is_hidden` instead, which reuses the already-fetched
    ``stat()`` result and costs no extra syscall.
    """
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


def _entry_is_hidden(entry: os.DirEntry, st: os.stat_result) -> bool:
    """Hidden check for a scandir entry, reusing its cached ``stat()``.

    On Windows the hidden flag is read from ``st_file_attributes`` carried by
    the stat result itself — this eliminates the per-file
    ``GetFileAttributesW`` ctypes call the old scanner made. Off Windows the
    dotfile convention needs no syscall at all.
    """
    if os.name == "nt":
        attrs = getattr(st, "st_file_attributes", None)
        if attrs is not None:
            return bool(attrs & _HIDDEN_ATTR)
        # Exotic stat implementations without st_file_attributes: fall back
        # to the single attribute query (same semantics as _is_hidden).
        try:
            import ctypes

            a = ctypes.windll.kernel32.GetFileAttributesW(win_long(entry.path))
            return a != -1 and bool(a & _HIDDEN_ATTR)
        except Exception:  # noqa: BLE001 - cannot determine -> treat as visible
            return False
    return entry.name.startswith(".")


@dataclass
class ScanResult:
    root: Path
    files: List[Path] = field(default_factory=list)
    by_category: Dict[str, int] = field(default_factory=dict)
    by_category_size: Dict[str, int] = field(default_factory=dict)
    total_size: int = 0
    # PHASE 1.2: per-file size in bytes keyed by ``str(path)``. The stat is
    # already performed below (``st.st_size``) — this simply keeps it so the
    # large-files discovery can sort by real bytes without a second stat pass.
    sizes: Dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.files)


def _date_label_from_ts(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m")


def _date_label(path: Path) -> str:
    try:
        ts = path.stat().st_mtime
    except OSError:
        ts = datetime.datetime.now().timestamp()
    return _date_label_from_ts(ts)


def _walk_files(
    root: Path,
    recursive: bool,
    skip_top_dirs: set,
) -> Iterator[Tuple[os.DirEntry, str, Path]]:
    """Yield ``(entry, top_name, logical_path)`` for files under *root*.

    Built on :func:`os.scandir`:

    - Each directory entry costs a **single** syscall. :class:`os.DirEntry`
      caches the ``stat()`` result, so the caller's ``is_file()`` / ``stat()``
      / size / mtime / hidden-attribute reads are all served from that one
      call. (The old implementation paid ~3 syscalls per file: ``is_file()``,
      a ctypes ``GetFileAttributesW`` for the hidden flag, and another
      ``stat()`` for size/mtime.)
    - Previously-organized output folders (category names / ``YYYY-MM`` dirs)
      are **pruned at the top level** instead of being descended into and
      filtered per file — same result, far less traversal on re-scans.

    ``top_name`` is the first path component under *root* (the file name
    itself for direct children), so the caller can apply the same
    first-component skip rule the old ``relative_to(root).parts[0]`` check
    implemented, without building a relative path per file. ``logical_path``
    is the plain :class:`Path` (no ``\\\\?\\`` prefix) for downstream use;
    only the ``scandir()`` call itself goes through :func:`win_long`.
    """
    # Stack items: (logical dir, top_name or None while at the first level).
    stack: List[Tuple[Path, Optional[str]]] = [(root, None)]
    while stack:
        d, top = stack.pop()
        try:
            with os.scandir(win_long(d)) as it:
                # Sorted for deterministic output: the same tree always
                # yields the same file order (and therefore the same plan /
                # move order), independent of filesystem enumeration order.
                entries = sorted(it, key=lambda e: e.name)
        except OSError:
            continue
        for entry in entries:
            try:
                is_dir = entry.is_dir(follow_symlinks=False)
            except OSError:
                continue
            if is_dir:
                if not recursive:
                    continue
                name = entry.name
                if top is None and (name in skip_top_dirs or is_date_dir(name)):
                    continue  # output of a previous run: do not descend
                stack.append((d / name, name if top is None else top))
            else:
                # Direct children report their own name as the "top" component,
                # mirroring the old parts[0] check for top-level files.
                yield entry, (top if top is not None else entry.name), d / entry.name


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
    skip_top_dirs = set(CATEGORY_NAMES.values()) | set(exclude_dirs)

    _log.info(
        "SCAN START root=%s mode=%s recursive=%s", root, mode, recursive
    )

    result = ScanResult(root=Path(root))

    for entry, first, logical in _walk_files(Path(root), recursive, skip_top_dirs):
        # Skip output folders from previous runs (both modes).
        if first in skip_top_dirs or is_date_dir(first):
            continue
        name = entry.name
        # P0-4: skip Windows system files & hidden files.
        if name.lower() in _SYSTEM_FILES:
            continue
        try:
            # follow_symlinks=True matches the old Path.is_file() semantics;
            # the stat result is cached on the entry (no extra syscall).
            if not entry.is_file():
                continue
            st = entry.stat()
        except OSError:
            continue
        if _entry_is_hidden(entry, st):
            continue
        if mode == "date":
            label = _date_label_from_ts(st.st_mtime)
        else:
            ext = os.path.splitext(name)[1].lower().lstrip(".")
            label = category_display(rules.get(ext, "others"))
        result.files.append(logical)
        result.by_category[label] = result.by_category.get(label, 0) + 1
        size = st.st_size
        # PHASE 1.2: keep the size we already computed (single stat pass).
        result.sizes[str(logical)] = size
        result.by_category_size[label] = result.by_category_size.get(label, 0) + size
        result.total_size += size

    _log.info(
        "SCAN DONE root=%s files=%d categories=%d total_bytes=%d",
        root, result.total, len(result.by_category), result.total_size,
    )
    return result
