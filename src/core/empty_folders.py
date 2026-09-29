"""Empty-folder discovery and safe, reversible cleanup (V1.2-A, feature 1).

Design (safety first — reuses the existing engine, adds NO new deletion path):

- **Detection is read-only and conservative.** A folder is reported only when
  its *entire* subtree contains no file at all, and it is not a hidden / system
  / junction / symbolic-link / reparse-point / permission-denied path. If we
  cannot *prove* a folder is safe, we do not report it.
- **Only the top-most empty folders are reported** (maximal subtrees). Moving
  the outermost folder already takes everything nested beneath it, and it also
  avoids quarantine target collisions.
- **"Cleanup" is a MOVE into a quarantine folder inside the same root**, executed
  by the SAME engine used for file organizing (:func:`core.organizer.move_items`).
  Nothing is ever deleted, every move is recorded in ``operations``, and the run
  is fully undoable through the existing undo path.

Nothing here touches the SQLite state directly, and the UI never implements its
own file-moving logic — both are hard requirements of the V1.2-A safety model.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from .organizer import OrganizeResult, PlanItem, move_items
from .scanner import _is_hidden  # reuse the canonical Windows hidden-attr check
from utils.logger import get_logger
from utils.paths import win_long

_log = get_logger("empty_folders")

# Quarantine folder created inside the scanned root. Anything moved here is
# reversible, and the name is excluded from every future scan.
QUARANTINE_DIRNAME = "_待清理空文件夹"
QUARANTINE_LABEL = "空文件夹"

# Directory names that must never be considered (Windows system / shell dirs).
SYSTEM_DIRS = frozenset({
    "system volume information",
    "$recycle.bin",
    "$winreagent",
    "recovery",
    "config.msi",
    "windows",
    "windowsapps",
})

# FILE_ATTRIBUTE_REPARSE_POINT — junction / mount point / symlink on Windows.
_REPARSE_POINT_ATTR = 0x400

ProgressCb = Callable[[int, int, str], None]


@dataclass
class EmptyFolder:
    """A top-most folder whose whole subtree contains no file."""

    path: Path
    nested: int = 0  # number of descendant folders that go with it
    mtime: float = 0.0

    @property
    def name(self) -> str:
        return self.path.name


@dataclass
class CleanupResult:
    planned: int = 0
    moved: int = 0
    failed: int = 0
    # Folders that were empty at scan time but gained content before execution
    # (TOCTOU). They are skipped, never silently removed.
    stale: List[str] = field(default_factory=list)
    result: Optional[OrganizeResult] = None


# --------------------------------------------------------------------------- #
# safety primitives
# --------------------------------------------------------------------------- #
def _is_reparse_point(path: Path) -> bool:
    """True for junctions / symlinks / mount points (or when undeterminable).

    Undeterminable is treated as True (i.e. "not safe"), so a folder we cannot
    inspect is never proposed for removal.
    """
    try:
        if os.path.islink(path):
            return True
    except OSError:
        return True
    if os.name == "nt":
        try:
            import ctypes

            attrs = ctypes.windll.kernel32.GetFileAttributesW(win_long(path))
            if attrs == -1:
                return True
            return bool(attrs & _REPARSE_POINT_ATTR)
        except Exception:  # noqa: BLE001 - cannot determine -> not safe
            return True
    return False


def _is_protected(path: Path) -> bool:
    """True if `path` must never be considered for cleanup."""
    if path.name == QUARANTINE_DIRNAME:
        return True
    if path.name.lower() in SYSTEM_DIRS:
        return True
    if _is_hidden(path):
        return True
    return _is_reparse_point(path)


def _scan_entries(d: Path):
    """List ``d`` (long-path safe). Returns ``None`` when unreadable.

    Entries are listed via the long-path form, but child paths are rebuilt from
    the *logical* parent + entry name so callers keep prefix-free ``Path``s.
    """
    try:
        with os.scandir(win_long(d)) as it:
            return list(it)
    except OSError:
        return None


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


# --------------------------------------------------------------------------- #
# detection
# --------------------------------------------------------------------------- #
def _walk(d: Path):
    """Return ``(subtree_is_empty, nested_folder_count, top_most_empty)``.

    Single pass. ``top_most_empty`` holds the *maximal* empty folders found
    under ``d`` — when a folder turns out to be empty its descendants' records
    are discarded (the folder supersedes them).
    """
    entries = _scan_entries(d)
    if entries is None:
        # unreadable -> not provably empty -> also means ancestors are not empty
        return (False, 0, [])
    if not entries:
        return (True, 0, [])

    nested = 0
    recorded: List[EmptyFolder] = []
    # `has_content` means "d itself is NOT empty". Crucially we must NOT abort
    # the loop when we find content: d's OTHER children may still be empty and
    # are legitimate cleanup candidates. So we mark and continue.
    has_content = False
    for e in entries:
        try:
            is_dir = e.is_dir(follow_symlinks=False)
        except OSError:
            has_content = True
            continue
        if not is_dir:
            # any non-directory entry (file, symlink, etc.) -> d has content
            has_content = True
            continue
        child = d / e.name
        if _is_protected(child):
            # a protected child means d itself cannot be removed
            has_content = True
            continue
        ok, n, sub = _walk(child)
        if ok:
            nested += 1 + n
            recorded.append(EmptyFolder(path=child, nested=n, mtime=_mtime(child)))
            # `sub` deliberately discarded: `child` supersedes its descendants
        else:
            recorded.extend(sub)

    if has_content:
        return (False, nested, recorded)
    return (True, nested, recorded)


def find_empty_folders(root: Path, recursive: bool = True) -> List[EmptyFolder]:
    """Return the top-most empty folders under ``root`` (read-only).

    ``recursive=False`` reports only direct children of ``root``. The root
    itself is never reported. Raises ``ValueError`` for the app's own data
    directory (it holds the SQLite DB).
    """
    root = Path(root)
    if not root.is_dir():
        return []

    # P0-4 (reused): never allow the app's own data directory.
    from data.database import data_dir

    if root.resolve() == data_dir().resolve():
        raise ValueError(
            "不能清理应用自身的数据目录（包含数据库文件），请选择其他文件夹。"
        )

    _log.info("EMPTY SCAN START root=%s recursive=%s", root, recursive)

    if recursive:
        _ok, _n, out = _walk(root)
    else:
        out = []
        for e in _scan_entries(root) or []:
            try:
                if not e.is_dir(follow_symlinks=False):
                    continue
            except OSError:
                continue
            child = root / e.name
            if _is_protected(child):
                continue
            ok, n, _sub = _walk(child)  # `_sub` discarded: direct children only
            if ok:
                out.append(EmptyFolder(path=child, nested=n, mtime=_mtime(child)))

    out.sort(key=lambda f: (len(f.path.parts), str(f.path)))
    _log.info("EMPTY SCAN DONE root=%s folders=%d", root, len(out))
    return out


def total_nested(folders: List[EmptyFolder]) -> int:
    """Total folders that will be moved (top-most + everything nested)."""
    return sum(1 + f.nested for f in folders)


# --------------------------------------------------------------------------- #
# plan + execute (reuses the existing move engine)
# --------------------------------------------------------------------------- #
def plan_cleanup(root: Path, folders: List[EmptyFolder]) -> List[PlanItem]:
    """Build a move plan: each folder -> ``<root>/<quarantine>/<relpath>``."""
    root = Path(root)
    quarantine = root / QUARANTINE_DIRNAME
    items: List[PlanItem] = []
    for f in folders:
        try:
            rel = Path(f.path).relative_to(root)
        except ValueError:
            continue  # not under root -> never touch it
        items.append(
            PlanItem(
                source=Path(f.path),
                target=quarantine / rel,
                category=QUARANTINE_LABEL,
            )
        )
    return items


def _still_empty(p: Path) -> bool:
    """TOCTOU re-check: is ``p`` *still* transitively empty?

    Uses exactly the same predicate as detection (:func:`_walk`), so a folder
    that merely contains other empty folders is still considered empty — a
    folder that gained any file (anywhere in its subtree) is not.
    """
    try:
        if not p.is_dir():
            return False
    except OSError:
        return False
    ok, _nested, _recorded = _walk(p)
    return ok


def cleanup(
    root: Path,
    folders: List[EmptyFolder],
    on_progress: Optional[ProgressCb] = None,
) -> CleanupResult:
    """Move the given empty folders into the quarantine folder.

    Every folder is re-verified as still-empty immediately before the move, so a
    folder that gained content after the scan is skipped (never removed). The
    actual move is delegated to :func:`core.organizer.move_items`.
    """
    items = plan_cleanup(root, folders)
    fresh: List[PlanItem] = []
    stale_paths: List[str] = []
    for it in items:
        if _still_empty(it.source):
            fresh.append(it)
        else:
            stale_paths.append(str(it.source))

    if stale_paths:
        _log.info("EMPTY CLEANUP stale skipped=%d", len(stale_paths))

    result = move_items(fresh, on_progress=on_progress)
    return CleanupResult(
        planned=len(items),
        moved=result.moved,
        failed=result.failed,
        stale=stale_paths,
        result=result,
    )
