"""PHASE 1.2 — Large File Discovery tests.

Covers the §13 acceptance matrix:
1. per-file size captured during scan (ScanResult.sizes)
2. large-file sorting (by real bytes, not formatted strings)
3. descending order
4. top-N truncation
5. zero-byte files
6. stat failure does not crash the scan
7. path preserved in results
8. human-readable size formatting (B/KB/MB/GB/TB)
9. page construction + navigation registration (offscreen)
10. existing regression (full suite runs separately in §14)

No real EXE, no real network, no deletion — discovery-only semantics.
"""
import os
import sys
import tempfile
from pathlib import Path

_TMP_HOME = tempfile.mkdtemp(prefix="dc_large_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from core import scan  # noqa: E402
from core.scanner import ScanResult  # noqa: E402
from ui.pages.large_files_page import (  # noqa: E402
    LargeFilesPage,
    TOP_N,
    collect_large_files,
)
from utils.format import human_size  # noqa: E402

app = QApplication.instance() or QApplication(["-platform", "offscreen"])


def _make_tree(spec: dict[str, int]) -> Path:
    """Create a temp dir with files ``relpath -> byte_size``."""
    src = Path(tempfile.mkdtemp(prefix="dc_large_src_"))
    for rel, nbytes in spec.items():
        p = src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * nbytes if nbytes > 0 else b"")
    return src


# --------------------------------------------------------------------------- #
# 1. per-file size captured
# --------------------------------------------------------------------------- #
def test_size_captured_per_file():
    src = _make_tree({"a.txt": 10, "b.bin": 2048})
    result = scan(src, mode="type")
    sizes = {Path(k).name: v for k, v in result.sizes.items()}
    assert sizes["a.txt"] == 10
    assert sizes["b.bin"] == 2048
    # existing aggregates stay intact
    assert result.total_size == 10 + 2048
    assert result.total == 2


# --------------------------------------------------------------------------- #
# 2/3. sorting by real bytes, descending
# --------------------------------------------------------------------------- #
def test_sorting_descending_and_path_preserved():
    src = _make_tree({"z.txt": 100, "a.txt": 1000, "m.bin": 500})
    result = scan(src, mode="type")
    entries = collect_large_files(result, limit=10)
    sizes = [e[1] for e in entries]
    assert sizes == sorted(sizes, reverse=True)
    # every entry's path is preserved exactly as scanned
    paths = {str(e[0]) for e in entries}
    assert paths == {str(f) for f in result.files}
    assert entries[0][0].name == "a.txt"  # largest first


def test_ties_broken_by_path_ascending():
    src = _make_tree({"b.txt": 100, "a.txt": 100, "c.txt": 100})
    result = scan(src, mode="type")
    entries = collect_large_files(result, limit=10)
    assert [e[0].name for e in entries] == ["a.txt", "b.txt", "c.txt"]


# --------------------------------------------------------------------------- #
# 4. top-N truncation
# --------------------------------------------------------------------------- #
def test_top_n_truncation():
    src = _make_tree({f"f{i:03}.txt": i for i in range(105)})
    result = scan(src, mode="type")
    entries = collect_large_files(result, TOP_N)
    assert len(entries) == TOP_N
    assert entries[0][0].name == "f104.txt"  # largest


def test_top_n_allowed_above_scan_size():
    # limit greater than file count -> returns all, never crashes
    src = _make_tree({"a.txt": 1, "b.txt": 2})
    result = scan(src, mode="type")
    entries = collect_large_files(result, 1000)
    assert len(entries) == 2


# --------------------------------------------------------------------------- #
# 5. zero-byte files
# --------------------------------------------------------------------------- #
def test_zero_byte_files_included():
    src = _make_tree({"empty.txt": 0, "big.bin": 500})
    result = scan(src, mode="type")
    entries = collect_large_files(result, limit=10)
    by_name = {e[0].name: e[1] for e in entries}
    assert by_name["empty.txt"] == 0
    assert entries[-1][0].name == "empty.txt"  # zero-byte sorts last


# --------------------------------------------------------------------------- #
# 6. stat failure does not crash scan
# --------------------------------------------------------------------------- #
def test_stat_failure_does_not_crash(monkeypatch):
    import pathlib

    # Build the tree first: tempfile.mkdtemp itself walks Path.stat.
    src = _make_tree({"a.txt": 5, "b.txt": 7})

    def _boom(self, *, follow_symlinks=True):
        raise OSError("stat failed")

    monkeypatch.setattr(pathlib.Path, "stat", _boom)
    result = scan(src, mode="type")  # must not raise
    entries = collect_large_files(result, limit=10)  # must not raise
    assert len(entries) >= 0  # scan completed; content may be empty
    # defensive: missing size key never breaks discovery
    empty = ScanResult(root=src, files=[src / "ghost.txt"])
    assert collect_large_files(empty, limit=10) == [(src / "ghost.txt", 0)]


# --------------------------------------------------------------------------- #
# 7. path preserved (explicit)
# --------------------------------------------------------------------------- #
def test_paths_preserved_in_entries():
    # nested file requires recursive scan (non-recursive glob is single-level)
    src = _make_tree({"nested/deep/video.mp4": 4096, "root.txt": 1})
    result = scan(src, mode="type", recursive=True)
    entries = collect_large_files(result, limit=10)
    paths = {str(e[0]) for e in entries}
    assert str(src / "nested" / "deep" / "video.mp4") in paths
    assert str(src / "root.txt") in paths
    assert entries[0][0].name == "video.mp4"  # largest


# --------------------------------------------------------------------------- #
# 8. human-readable size formatting
# --------------------------------------------------------------------------- #
def test_human_size_formatting():
    assert human_size(0) == "0 B"
    assert human_size(1023) == "1023 B"
    assert human_size(1024) == "1.0 KB"
    assert human_size(5 * 1024**2) == "5.0 MB"
    assert human_size(842 * 1024**2) == "842.0 MB"
    assert human_size(1024**3) == "1.0 GB"
    assert human_size(1024**4) == "1.0 TB"


# --------------------------------------------------------------------------- #
# 9. page construction + navigation registration
# --------------------------------------------------------------------------- #
def test_page_construction():
    page = LargeFilesPage()
    assert page._scan_btn.text() == "开始扫描"
    assert page._recursive_toggle.is_on() is False
    assert page._source is not None


def test_navigation_registration(monkeypatch):
    import ui.app_shell as shell_mod
    from ui.app_shell import AppShell

    monkeypatch.setattr(shell_mod, "should_show_welcome", lambda: False)
    shell = AppShell()
    assert "large" in shell._pages
    assert isinstance(shell._pages["large"], LargeFilesPage)
    assert "large" in shell.sidebar._buttons
