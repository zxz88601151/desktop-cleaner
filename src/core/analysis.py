"""Read-only folder analysis (V1.2-A, feature 2).

Produces a structural snapshot of a folder tree — total size, file / folder
counts, type distribution, largest files and folders, the most recently
modified files, and the empty folders — **without ever modifying anything**.

Design notes
------------
- **Read-only.** There is no write path in this module at all: no file is
  created, moved, renamed or deleted. Analysis can never alter filesystem
  state.
- **One traversal, one fold.** An iterative (non-recursive) walk collects
  directory/file facts; subtree sizes are then folded in a second in-memory
  pass in reverse discovery order. Because a child is always discovered after
  its parent, reverse discovery order is a valid post-order — so there is no
  recursion and therefore no path-depth limit.
- **Reparse points are never followed.** Junctions / symlinks / mount points
  are skipped and counted (``skipped``), so the walk can neither loop forever
  nor double-count a linked subtree.
- **Long-path safe.** Every directory listing goes through ``win_long``.
- **Stable keys, never UI text.** ``by_category`` is keyed by the stable
  category *key* (``images`` / ``documents`` / ...), not by its Chinese display
  label, so the result is safe to serialise and export without scraping UI
  copy. The UI maps keys to labels via :func:`core.rules.category_display`.
- **Rules reuse.** Extension -> category comes from :mod:`core.classifier` /
  :mod:`core.rules`; this module owns no rule table of its own.
- **Empty folders reuse** :func:`core.empty_folders.find_empty_folders`, so the
  "analysis" view and the "empty folder cleanup" feature can never disagree
  about what counts as empty. That is a deliberate second (read-only) pass.

The result object is export-friendly (:meth:`AnalysisResult.to_dict`) so the
Export Report feature can serialise it without touching the UI layer.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .classifier import classify
from .empty_folders import _is_reparse_point, _scan_entries, find_empty_folders
from .rules import DEFAULT_RULES
from utils.logger import get_logger

_log = get_logger("analysis")

# Bucket label for files with no extension. Kept as a stable, language-neutral
# key; the UI decides how to render it.
NO_EXTENSION = "(none)"

# Emit a progress tick every N visited directories (avoids signal spam).
_PROGRESS_EVERY = 200

ProgressCb = Callable[[int, int, str], None]


# --------------------------------------------------------------------------- #
# data model
# --------------------------------------------------------------------------- #
@dataclass
class FileEntry:
    """A single file, with the size/mtime already stat'ed during the walk."""

    path: Path
    size: int
    mtime: float

    @property
    def name(self) -> str:
        return self.path.name

    def to_dict(self) -> dict:
        return {"path": str(self.path), "size": self.size, "mtime": self.mtime}


@dataclass
class FolderEntry:
    """A folder plus the aggregate size of its whole subtree."""

    path: Path
    total_size: int          # bytes in this folder's entire subtree
    file_count: int          # files directly inside (non-recursive)
    folder_count: int        # subfolders directly inside (non-recursive)

    @property
    def name(self) -> str:
        return self.path.name

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "total_size": self.total_size,
            "file_count": self.file_count,
            "folder_count": self.folder_count,
        }


@dataclass
class AnalysisResult:
    """Immutable-by-convention snapshot of one folder tree."""

    root: Path
    total_size: int = 0
    file_count: int = 0
    folder_count: int = 0                                    # excludes root
    by_category: Dict[str, int] = field(default_factory=dict)       # key -> files
    by_category_size: Dict[str, int] = field(default_factory=dict)  # key -> bytes
    by_extension: Dict[str, int] = field(default_factory=dict)      # ext -> files
    by_extension_size: Dict[str, int] = field(default_factory=dict)  # ext -> bytes
    largest_files: List[FileEntry] = field(default_factory=list)
    largest_folders: List[FolderEntry] = field(default_factory=list)
    recent_files: List[FileEntry] = field(default_factory=list)
    empty_folders: List[str] = field(default_factory=list)   # str paths
    skipped: int = 0                                         # unreadable / links
    duration_ms: int = 0

    @property
    def avg_file_size(self) -> int:
        return self.total_size // self.file_count if self.file_count else 0

    def to_dict(self) -> dict:
        """JSON-serialisable form (stable field names; byte units explicit)."""
        return {
            "root": str(self.root),
            "total_size_bytes": self.total_size,
            "file_count": self.file_count,
            "folder_count": self.folder_count,
            "skipped": self.skipped,
            "duration_ms": self.duration_ms,
            "by_category": [
                {
                    "category": k,
                    "files": self.by_category[k],
                    "size_bytes": self.by_category_size.get(k, 0),
                }
                for k in self.by_category
            ],
            "by_extension": [
                {
                    "extension": k,
                    "files": self.by_extension[k],
                    "size_bytes": self.by_extension_size.get(k, 0),
                }
                for k in self.by_extension
            ],
            "largest_files": [f.to_dict() for f in self.largest_files],
            "largest_folders": [f.to_dict() for f in self.largest_folders],
            "recent_files": [f.to_dict() for f in self.recent_files],
            "empty_folders": list(self.empty_folders),
        }


# --------------------------------------------------------------------------- #
# traversal
# --------------------------------------------------------------------------- #
def _collect(root: Path, on_progress: Optional[ProgressCb]):
    """Single iterative walk. Returns raw per-directory facts + file list.

    Returns ``(dirs, parent_of, direct_size, direct_files, direct_subdirs,
    files, skipped)``.
    """
    dirs: List[Path] = []
    parent_of: Dict[str, str] = {}
    direct_size: Dict[str, int] = {}
    direct_files: Dict[str, int] = {}
    direct_subdirs: Dict[str, int] = {}
    files: List[FileEntry] = []
    skipped = 0

    stack: List[Path] = [root]
    while stack:
        d = stack.pop()
        key = str(d)
        dirs.append(d)
        dsize = dfiles = ddirs = 0

        entries = _scan_entries(d)
        if entries is None:
            # unreadable (permission denied / vanished) -> count, keep going
            skipped += 1
        else:
            for e in entries:
                try:
                    is_dir = e.is_dir(follow_symlinks=False)
                except OSError:
                    skipped += 1
                    continue
                if is_dir:
                    child = d / e.name
                    if _is_reparse_point(child):
                        skipped += 1          # junction/symlink: never followed
                        continue
                    ddirs += 1
                    parent_of[str(child)] = key
                    stack.append(child)
                    continue
                try:
                    if not e.is_file(follow_symlinks=False):
                        continue              # symlinked file: not counted
                    st = e.stat()
                except OSError:
                    skipped += 1
                    continue
                dsize += st.st_size
                dfiles += 1
                files.append(
                    FileEntry(path=d / e.name, size=st.st_size, mtime=st.st_mtime)
                )

        direct_size[key] = dsize
        direct_files[key] = dfiles
        direct_subdirs[key] = ddirs

        if on_progress is not None and len(dirs) % _PROGRESS_EVERY == 0:
            on_progress(len(dirs), 0, f"正在分析… 已扫描 {len(dirs)} 个文件夹")

    return dirs, parent_of, direct_size, direct_files, direct_subdirs, files, skipped


def _fold_subtree_sizes(dirs, parent_of, direct_size) -> Dict[str, int]:
    """Fold per-directory direct sizes into whole-subtree sizes.

    Reverse discovery order is a valid post-order (a child is always appended
    after its parent), so every child is finalised before its parent is read.
    """
    subtree = dict(direct_size)
    for d in reversed(dirs):
        key = str(d)
        parent = parent_of.get(key)
        if parent is not None:
            subtree[parent] = subtree.get(parent, 0) + subtree[key]
    return subtree


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def analyze(
    root,
    rules: Optional[Dict[str, str]] = None,
    top_n: int = 20,
    include_empty: bool = True,
    on_progress: Optional[ProgressCb] = None,
) -> AnalysisResult:
    """Analyse ``root`` and return an :class:`AnalysisResult` (read-only).

    ``top_n`` bounds the three ranked lists (largest files / largest folders /
    recent files). ``include_empty`` toggles the empty-folder pass (a second
    read-only walk) so callers can skip it for very large trees.

    Raises ``ValueError`` for the app's own data directory (it holds the DB).
    """
    root = Path(root)
    rules = rules or DEFAULT_RULES
    res = AnalysisResult(root=root)
    if not root.is_dir():
        return res

    # P0-4 (reused): never analyse the app's own data directory.
    from data.database import data_dir

    if root.resolve() == data_dir().resolve():
        raise ValueError(
            "不能分析应用自身的数据目录（包含数据库文件），请选择其他文件夹。"
        )

    t0 = time.perf_counter()
    _log.info("ANALYZE START root=%s top_n=%d", root, top_n)

    (
        dirs,
        parent_of,
        direct_size,
        direct_files,
        direct_subdirs,
        files,
        skipped,
    ) = _collect(root, on_progress)

    subtree = _fold_subtree_sizes(dirs, parent_of, direct_size)

    res.total_size = subtree.get(str(root), 0)
    res.file_count = len(files)
    res.folder_count = max(0, len(dirs) - 1)   # every visited dir except root
    res.skipped = skipped

    # --- distributions (stable keys only) -------------------------------- #
    by_cat: Dict[str, int] = {}
    by_cat_size: Dict[str, int] = {}
    by_ext: Dict[str, int] = {}
    by_ext_size: Dict[str, int] = {}
    for f in files:
        cat = classify(f.path, rules)
        by_cat[cat] = by_cat.get(cat, 0) + 1
        by_cat_size[cat] = by_cat_size.get(cat, 0) + f.size
        ext = f.path.suffix.lower().lstrip(".") or NO_EXTENSION
        by_ext[ext] = by_ext.get(ext, 0) + 1
        by_ext_size[ext] = by_ext_size.get(ext, 0) + f.size

    # Order both views by size desc, then by key for a deterministic tie-break.
    res.by_category = {
        k: by_cat[k]
        for k in sorted(by_cat, key=lambda k: (-by_cat_size.get(k, 0), k))
    }
    res.by_category_size = by_cat_size
    res.by_extension = {
        k: by_ext[k]
        for k in sorted(by_ext, key=lambda k: (-by_ext_size.get(k, 0), k))
    }
    res.by_extension_size = by_ext_size

    # --- ranked lists ----------------------------------------------------- #
    res.largest_files = sorted(files, key=lambda f: (-f.size, str(f.path)))[:top_n]
    res.recent_files = sorted(files, key=lambda f: (-f.mtime, str(f.path)))[:top_n]

    root_key = str(root)
    folder_entries = [
        FolderEntry(
            path=d,
            total_size=subtree.get(str(d), 0),
            file_count=direct_files.get(str(d), 0),
            folder_count=direct_subdirs.get(str(d), 0),
        )
        for d in dirs
        if str(d) != root_key
    ]
    res.largest_folders = sorted(
        folder_entries, key=lambda x: (-x.total_size, str(x.path))
    )[:top_n]

    # --- empty folders (reuse the canonical, conservative detector) -------- #
    if include_empty:
        res.empty_folders = [
            str(f.path) for f in find_empty_folders(root, recursive=True)
        ]

    res.duration_ms = int((time.perf_counter() - t0) * 1000)
    _log.info(
        "ANALYZE DONE root=%s files=%d folders=%d bytes=%d empty=%d skipped=%d ms=%d",
        root, res.file_count, res.folder_count, res.total_size,
        len(res.empty_folders), res.skipped, res.duration_ms,
    )
    return res
