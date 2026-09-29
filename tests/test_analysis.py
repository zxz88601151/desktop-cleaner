"""V1.2-A feature 2 — folder analysis (Qt-free).

Run:  pytest tests/test_analysis.py       (or: python tests/test_analysis.py)

Properties asserted here:
  - total size / file count / folder count are exact
  - category distribution uses STABLE KEYS (never UI text)
  - extension distribution and both ranked file lists are correct
  - largest folders aggregate the whole subtree (parent >= child)
  - empty folders reuse the canonical detector
  - reparse points (junctions / symlinks) are skipped, never followed
  - the app's own data directory is refused
  - the result serialises to JSON without a UI layer
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

_TMP_HOME = tempfile.mkdtemp(prefix="dc_analysis_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import core.analysis as analysis  # noqa: E402
from core import analyze  # noqa: E402
from data import database  # noqa: E402

database.init_db()


def _assert(cond: bool, msg: str):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("  ok:", msg)


def _tree() -> Path:
    """docs/{a.pdf=100,b.txt=200}, pics/{c.jpg=1000}, notes.md=50, empty_dir/"""
    base = Path(tempfile.mkdtemp(prefix="dc_a_"))
    (base / "docs").mkdir()
    (base / "pics").mkdir()
    (base / "empty_dir").mkdir()
    (base / "docs" / "a.pdf").write_bytes(b"a" * 100)
    (base / "docs" / "b.txt").write_bytes(b"b" * 200)
    (base / "pics" / "c.jpg").write_bytes(b"c" * 1000)
    (base / "notes.md").write_bytes(b"n" * 50)
    return base


# --------------------------------------------------------------------------- #
def test_counts_and_total_size():
    print("[1] counts + total size")
    base = _tree()
    r = analyze(base)
    _assert(r.total_size == 1350, f"total_size == 1350 (got {r.total_size})")
    _assert(r.file_count == 4, f"file_count == 4 (got {r.file_count})")
    _assert(r.folder_count == 3, f"folder_count == 3 (got {r.folder_count})")
    _assert(r.skipped == 0, f"nothing skipped (got {r.skipped})")


def test_category_distribution_uses_stable_keys():
    print("[2] category distribution uses stable keys, not UI text")
    base = _tree()
    r = analyze(base)
    _assert(
        set(r.by_category) == {"documents", "images"},
        f"keys are stable category keys (got {sorted(r.by_category)})",
    )
    _assert(r.by_category["documents"] == 3, "documents == 3 files")
    _assert(r.by_category["images"] == 1, "images == 1 file")
    _assert(r.by_category_size["images"] == 1000, "images size == 1000")
    _assert(r.by_category_size["documents"] == 350, "documents size == 350")
    _assert(
        "文档" not in r.by_category and "图片" not in r.by_category,
        "no Chinese UI label leaks into the data model",
    )


def test_extension_distribution():
    print("[3] extension distribution")
    base = _tree()
    r = analyze(base)
    _assert(set(r.by_extension) == {"pdf", "txt", "jpg", "md"},
            f"extensions (got {sorted(r.by_extension)})")
    _assert(r.by_extension_size["jpg"] == 1000, "jpg bytes == 1000")


def test_largest_files_ranked():
    print("[4] largest files ranked by size")
    base = _tree()
    r = analyze(base, top_n=3)
    names = [f.name for f in r.largest_files]
    _assert(names == ["c.jpg", "b.txt", "a.pdf"], f"order (got {names})")
    _assert(r.largest_files[0].size == 1000, "top file is 1000 bytes")


def test_largest_folders_aggregate_subtree():
    print("[5] largest folders aggregate the whole subtree")
    base = _tree()
    r = analyze(base)
    by_name = {f.name: f for f in r.largest_folders}
    _assert(set(by_name) == {"docs", "pics", "empty_dir"},
            f"all non-root folders listed (got {sorted(by_name)})")
    _assert(by_name["pics"].total_size == 1000, "pics subtree == 1000")
    _assert(by_name["docs"].total_size == 300, "docs subtree == 300")
    _assert(by_name["docs"].file_count == 2, "docs direct files == 2")
    _assert(by_name["empty_dir"].total_size == 0, "empty_dir subtree == 0")

    # nested: a parent's subtree must be >= any child's subtree
    nested = Path(tempfile.mkdtemp(prefix="dc_a5_"))
    (nested / "outer" / "inner").mkdir(parents=True)
    (nested / "outer" / "inner" / "x.bin").write_bytes(b"x" * 500)
    (nested / "outer" / "y.bin").write_bytes(b"y" * 100)
    r2 = analyze(nested)
    d = {f.name: f for f in r2.largest_folders}
    _assert(d["outer"].total_size == 600, "outer subtree == 600")
    _assert(d["inner"].total_size == 500, "inner subtree == 500")
    _assert(d["outer"].total_size >= d["inner"].total_size,
            "parent subtree >= child subtree")
    _assert(r2.folder_count == 2, "folder_count counts nested dirs too")


def test_recent_files_ranked_by_mtime():
    print("[6] recent files ranked by mtime desc")
    base = _tree()
    os.utime(base / "notes.md", (2_000_000_000, 2_000_000_000))
    os.utime(base / "docs" / "a.pdf", (1_000_000_000, 1_000_000_000))
    os.utime(base / "docs" / "b.txt", (1_500_000_000, 1_500_000_000))
    os.utime(base / "pics" / "c.jpg", (1_200_000_000, 1_200_000_000))
    r = analyze(base)
    names = [f.name for f in r.recent_files]
    _assert(names == ["notes.md", "b.txt", "c.jpg", "a.pdf"],
            f"recent order (got {names})")


def test_empty_folders_reused():
    print("[7] empty folders come from the canonical detector")
    base = _tree()
    r = analyze(base)
    _assert(
        [Path(p).name for p in r.empty_folders] == ["empty_dir"],
        f"empty folders (got {r.empty_folders})",
    )
    r2 = analyze(base, include_empty=False)
    _assert(r2.empty_folders == [], "include_empty=False skips the empty pass")


def test_reparse_points_are_skipped():
    print("[8] reparse points are skipped, never followed")
    base = _tree()
    real = analysis._is_reparse_point
    analysis._is_reparse_point = lambda p: Path(p).name == "pics"
    try:
        r = analyze(base)
    finally:
        analysis._is_reparse_point = real
    _assert(r.file_count == 3, f"file inside the link not counted (got {r.file_count})")
    _assert(r.total_size == 350, f"link size excluded (got {r.total_size})")
    _assert(r.folder_count == 2, f"link dir not counted (got {r.folder_count})")
    _assert(r.skipped == 1, f"the link is reported as skipped (got {r.skipped})")
    _assert("pics" not in {f.name for f in r.largest_folders}, "link not listed")


def test_missing_root_returns_empty():
    print("[9] missing root -> empty result (no crash)")
    r = analyze(Path(tempfile.mkdtemp(prefix="dc_a9_")) / "does_not_exist")
    _assert(r.file_count == 0 and r.total_size == 0, "empty result for missing root")


def test_app_data_dir_refused():
    print("[10] app data directory is refused")
    raised = False
    try:
        analyze(database.data_dir())
    except ValueError:
        raised = True
    _assert(raised, "analysing the app data directory raises ValueError")


def test_to_dict_is_json_serialisable():
    print("[11] to_dict() is JSON-serialisable (export-ready)")
    base = _tree()
    r = analyze(base, top_n=2)
    payload = r.to_dict()
    text = json.dumps(payload, ensure_ascii=False)
    back = json.loads(text)
    _assert(back["total_size_bytes"] == 1350, "total_size_bytes round-trips")
    _assert(back["file_count"] == 4, "file_count round-trips")
    _assert(back["by_category"][0]["category"] in {"documents", "images"},
            "category entries carry the stable key")
    _assert(len(back["largest_files"]) == 2, "top_n honoured in the export")
    _assert(all("size" in f and "path" in f for f in back["largest_files"]),
            "file entries expose path + size")


def main():
    database.init_db()
    test_counts_and_total_size()
    test_category_distribution_uses_stable_keys()
    test_extension_distribution()
    test_largest_files_ranked()
    test_largest_folders_aggregate_subtree()
    test_recent_files_ranked_by_mtime()
    test_empty_folders_reused()
    test_reparse_points_are_skipped()
    test_missing_root_returns_empty()
    test_app_data_dir_refused()
    test_to_dict_is_json_serialisable()
    print("\nALL ANALYSIS TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(_TMP_HOME, ignore_errors=True)
