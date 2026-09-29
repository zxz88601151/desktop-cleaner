"""V1.2-A feature 1 — empty-folder discovery + reversible cleanup (Qt-free).

Run:  PYTHONPATH=src python tests/test_empty_folders.py   (or via pytest)

Safety properties asserted here:
  - only TOP-MOST empty folders are reported, with a correct nested count
  - anything containing a file / hidden dir / junction / reparse point is NOT
    reported (conservative)
  - cleanup is a MOVE into a quarantine folder (nothing deleted)
  - the run is recorded in `operations` and is fully undoable
  - a folder that gains content after the scan (TOCTOU) is skipped, not removed
  - the app's own data directory is refused
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_TMP_HOME = tempfile.mkdtemp(prefix="dc_empty_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core import (  # noqa: E402
    cleanup,
    execute_undo,
    find_empty_folders,
    plan_cleanup,
    total_nested,
)
from core.empty_folders import QUARANTINE_DIRNAME  # noqa: E402
from data import database  # noqa: E402
from data import history_repo, operation_repo  # noqa: E402

database.init_db()


def _assert(cond: bool, msg: str):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("  ok:", msg)


def _mkdirs(base: Path, *rels):
    for r in rels:
        (base / r).mkdir(parents=True, exist_ok=True)


def _names(folders) -> set:
    return {f.path.name for f in folders}


# --------------------------------------------------------------------------- #
def test_detection_topmost_and_nested():
    print("[1] detection: top-most only + nested count")
    base = Path(tempfile.mkdtemp(prefix="dc_e1_"))
    # a/b/c is a 3-deep empty chain; only `a` must be reported, nested=2
    _mkdirs(base, "a/b/c", "solo", "full")
    (base / "full" / "f.txt").write_bytes(b"x")
    # a non-empty branch that CONTAINS an empty leaf -> the leaf is reported
    _mkdirs(base, "keep/inner_empty")

    got = find_empty_folders(base, recursive=True)
    names = _names(got)
    _assert("a" in names, "top-most empty chain reported ('a')")
    _assert("b" not in names and "c" not in names, "nested empties superseded by 'a'")
    a = next(f for f in got if f.path.name == "a")
    _assert(a.nested == 2, f"'a' nested count == 2 (got {a.nested})")
    _assert("solo" in names, "standalone empty folder reported")
    _assert("full" not in names, "folder containing a file NOT reported")
    # SEMANTICS (locked): "empty" means the WHOLE subtree holds no file, so a
    # folder whose only content is an empty subfolder IS reported — as the
    # top-most entry, superseding that subfolder.
    _assert("keep" in names, "folder whose whole subtree is empty IS reported")
    _assert("inner_empty" not in names, "its empty child is superseded by the parent")
    _assert(
        total_nested(got) == (1 + 2) + (1 + 1) + (1 + 0),
        f"total_nested counts every folder that moves (got {total_nested(got)})",
    )


def test_non_recursive_direct_children_only():
    print("[2] non-recursive: direct children only")
    base = Path(tempfile.mkdtemp(prefix="dc_e2_"))
    _mkdirs(base, "top_empty", "keep/deep_empty")
    got = find_empty_folders(base, recursive=False)
    names = _names(got)
    _assert("top_empty" in names, "direct empty child reported")
    _assert("deep_empty" not in names, "deeper empty NOT reported in non-recursive mode")
    _assert("keep" in names, "a direct child that is transitively empty is reported")
    _assert(
        all("/" not in f.path.name for f in got), "non-recursive returns direct children only"
    )


def test_conservative_guards():
    print("[3] conservative guards: hidden / junction / reparse")
    base = Path(tempfile.mkdtemp(prefix="dc_e3_"))
    _mkdirs(base, "visible_empty", "hidden_empty")

    hid_ok = False
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.kernel32.SetFileAttributesW(
                str(base / "hidden_empty"),
                0x2 | 0x10,  # FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_DIRECTORY
            )
            hid_ok = True
        except Exception:  # noqa: BLE001
            hid_ok = False

    got = find_empty_folders(base, recursive=True)
    names = _names(got)
    _assert("visible_empty" in names, "normal empty folder reported")
    if hid_ok:
        _assert("hidden_empty" not in names, "hidden empty folder NOT reported")
    else:
        print("  (skip) hidden-attr check unavailable")

    # junction (mklink /J needs no admin on Windows)
    junc_base = Path(tempfile.mkdtemp(prefix="dc_e3j_"))
    _mkdirs(junc_base, "real_empty", "parent")
    made = False
    if os.name == "nt":
        r = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(junc_base / "parent" / "link"),
             str(junc_base / "real_empty")],
            capture_output=True,
        )
        made = r.returncode == 0
    if made:
        got2 = find_empty_folders(junc_base, recursive=True)
        n2 = _names(got2)
        _assert("link" not in n2, "junction NOT reported")
        _assert("parent" not in n2, "parent holding a junction NOT reported")
        _assert("real_empty" in n2, "the junction's real target is still eligible")
        # remove the junction itself (never its target) so TEMP stays tidy
        try:
            os.rmdir(junc_base / "parent" / "link")
        except OSError:
            pass
    else:
        print("  (skip) junction creation unavailable on this host")


def test_quarantine_is_excluded():
    print("[4] quarantine folder is never re-reported")
    base = Path(tempfile.mkdtemp(prefix="dc_e4_"))
    _mkdirs(base, f"{QUARANTINE_DIRNAME}/x/y")
    got = find_empty_folders(base, recursive=True)
    _assert(QUARANTINE_DIRNAME not in _names(got), "quarantine dir excluded from scan")


def test_cleanup_and_undo_roundtrip():
    print("[5] cleanup -> quarantine -> recorded -> undo restores")
    base = Path(tempfile.mkdtemp(prefix="dc_e5_"))
    _mkdirs(base, "a/b/c", "solo")
    (base / "keep.txt").write_bytes(b"keep")

    folders = find_empty_folders(base, recursive=True)
    _assert(_names(folders) == {"a", "solo"}, "expected exactly {a, solo}")

    items = plan_cleanup(base, folders)
    hid = history_repo.create(str(base), "empty_folders", len(items))
    operation_repo.bulk_insert_pending(hid, items)
    res = cleanup(base, folders)
    operation_repo.update_statuses_by_target(
        hid,
        {str(i.target) for i in res.result.items},
        {str(i.target) for i in res.result.failed_items},
    )
    history_repo.update_status(hid, "done", res.moved, 0)

    _assert(res.moved == 2, f"2 top-most folders moved (got {res.moved})")
    _assert(not (base / "a").exists(), "source 'a' no longer in place")
    _assert(not (base / "solo").exists(), "source 'solo' no longer in place")
    q = base / QUARANTINE_DIRNAME
    _assert((q / "a" / "b" / "c").is_dir(), "whole subtree preserved under quarantine")
    _assert((q / "solo").is_dir(), "'solo' preserved under quarantine")
    _assert((base / "keep.txt").exists(), "unrelated file untouched")

    # re-scan must find nothing new (quarantine excluded)
    _assert(find_empty_folders(base, recursive=True) == [], "nothing left to clean")

    # undo (core-level, mirrors the real run_undo chain)
    ops = operation_repo.list_by_history(hid)
    ur = execute_undo(ops)
    failed = operation_repo.apply_undo_result(hid, ur)
    _assert(failed == [], "undo reports no failures")
    _assert((base / "a" / "b" / "c").is_dir(), "'a/b/c' restored to the original root")
    _assert((base / "solo").is_dir(), "'solo' restored")


def test_toctou_stale_is_skipped():
    print("[6] TOCTOU: folder that gains content is skipped, not removed")
    base = Path(tempfile.mkdtemp(prefix="dc_e6_"))
    _mkdirs(base, "was_empty", "other_empty")
    folders = find_empty_folders(base, recursive=True)
    _assert(_names(folders) == {"was_empty", "other_empty"}, "both detected as empty")

    # someone drops a file in after the scan, before execution
    (base / "was_empty" / "new.txt").write_bytes(b"important")

    res = cleanup(base, folders)
    _assert(res.moved == 1, f"only the still-empty folder moved (got {res.moved})")
    _assert(len(res.stale) == 1 and res.stale[0].endswith("was_empty"),
            "the changed folder is reported as stale")
    _assert((base / "was_empty" / "new.txt").exists(), "user's new file NOT removed")
    _assert((base / QUARANTINE_DIRNAME / "other_empty").is_dir(), "other folder quarantined")


def test_app_data_dir_refused():
    print("[7] app data directory is refused")
    raised = False
    try:
        find_empty_folders(database.data_dir(), recursive=True)
    except ValueError:
        raised = True
    _assert(raised, "cleaning the app data directory raises ValueError")


def main():
    database.init_db()
    test_detection_topmost_and_nested()
    test_non_recursive_direct_children_only()
    test_conservative_guards()
    test_quarantine_is_excluded()
    test_cleanup_and_undo_roundtrip()
    test_toctou_stale_is_skipped()
    test_app_data_dir_refused()
    print("\nALL EMPTY-FOLDER TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(_TMP_HOME, ignore_errors=True)
