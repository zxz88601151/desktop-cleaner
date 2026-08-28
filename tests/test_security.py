"""P0 security / data-consistency regression tests (no UI, Qt-free).

Run:  PYTHONPATH=src python tests/test_security.py

Covers the four Phase-2 P0 fixes:
  - P0-1  organize interrupt -> operations stay undoable (pending + reconcile)
  - P0-2  partial undo failure is NOT reported as full success
  - P0-3  undo never overwrites an existing file at the restore target
  - P0-4  scanner skips system / hidden files and refuses the app data dir
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Isolate the SQLite DB into a temp dir via env override (before any import).
_TMP_HOME = tempfile.mkdtemp(prefix="dc_sec_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core import organize, plan, scan, execute_undo  # noqa: E402
from data import database  # noqa: E402
from data import history_repo, operation_repo  # noqa: E402

# Ensure schema exists for every runner (pytest does NOT call main(), which is
# the only place that previously triggered init_db). Idempotent; safe in both
# the `python tests/test_security.py` and `pytest` invocation paths.
database.init_db()


def _assert(cond: bool, msg: str):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("  ok:", msg)


def _make_source(names, base=None) -> Path:
    src = base or Path(tempfile.mkdtemp(prefix="dc_sec_src_"))
    for n in names:
        (src / n).write_bytes(b"data")
    return src


def _new_history(src, mode="type", total=0):
    return history_repo.create(str(src), mode, total)


# --------------------------------------------------------------------------- #
# P0-1: organize interrupt -> operations stay undoable
# --------------------------------------------------------------------------- #
def test_interrupt_recovery():
    print("[P0-1] 整理中断恢复 (pending + reconcile)")
    src = _make_source(["a.jpg", "b.jpg", "c.pdf"])
    items = plan(src, mode="type")
    _assert(len(items) == 3, "3 files planned")

    hid = _new_history(src, "type", 3)
    operation_repo.bulk_insert_pending(hid, items)  # recorded BEFORE any move

    # Simulate an interrupt: only a.jpg and b.jpg were actually moved.
    by_name = {it.source.name: it.target for it in items}
    for name in ("a.jpg", "b.jpg"):
        t = by_name[name]
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src / name), str(t))

    # A crash now would leave the DB with pending ops + some real moves.
    # At next startup reconcile_pending() must calibrate without moving files.
    operation_repo.reconcile_pending()

    ops = operation_repo.list_by_history(hid)
    status = {op["file_name"]: op["status"] for op in ops}
    _assert(status.get("a.jpg") == "moved", "a.jpg reconciled -> moved")
    _assert(status.get("b.jpg") == "moved", "b.jpg reconciled -> moved")
    _assert(status.get("c.pdf") == "failed", "c.pdf (never moved) -> failed")
    _assert(all(s != "pending" for s in status.values()), "no op left 'pending'")


# --------------------------------------------------------------------------- #
# P0-2: partial undo failure must NOT be reported as full success
# --------------------------------------------------------------------------- #
def test_partial_undo_no_false_success():
    print("[P0-2] 部分撤销失败不误标记")

    # --- partial failure branch ---
    src = _make_source(["a.jpg", "b.jpg", "c.pdf"])
    r = organize(src, mode="type")
    _assert(r.moved == 3, "3 files organized")
    hid = _new_history(src, "type", 3)
    operation_repo.bulk_insert(hid, r.items)  # status 'moved'
    history_repo.update_status(hid, "done", r.moved, 0)

    ops = operation_repo.list_by_history(hid)
    victim = ops[0]
    # Remove the file that currently sits at the victim's target so undo fails.
    Path(victim["target_path"]).unlink()

    result = execute_undo(ops)
    failed_files = operation_repo.apply_undo_result(hid, result)

    _assert(len(failed_files) >= 1, "undo reported at least one failure")
    ops_after = operation_repo.list_by_history(hid)
    victim_after = next(o for o in ops_after if o["id"] == victim["id"])
    _assert(victim_after["status"] == "moved", "failed op stays 'moved' (no false success)")
    others = [o for o in ops_after if o["id"] != victim["id"]]
    _assert(all(o["status"] == "undone" for o in others), "successfully restored ops -> 'undone'")

    # --- full success branch ---
    src2 = _make_source(["x.jpg", "y.pdf"])
    r2 = organize(src2, mode="type")
    hid2 = _new_history(src2, "type", 2)
    operation_repo.bulk_insert(hid2, r2.items)
    history_repo.update_status(hid2, "done", r2.moved, 0)
    ops2 = operation_repo.list_by_history(hid2)
    res2 = execute_undo(ops2)
    ff2 = operation_repo.apply_undo_result(hid2, res2)
    _assert(ff2 == [], "fully successful undo returns empty failure list")
    ops2_after = operation_repo.list_by_history(hid2)
    _assert(all(o["status"] == "undone" for o in ops2_after), "all ops 'undone' on full success")


# --------------------------------------------------------------------------- #
# P0-3: undo never overwrites an existing file at the restore target
# --------------------------------------------------------------------------- #
def test_undo_no_overwrite():
    print("[P0-3] 撤销碰撞保护（不覆盖）")
    src = _make_source(["a.jpg"])
    r = organize(src, mode="type")
    _assert(r.moved == 1, "1 file organized")

    hid = _new_history(src, "type", 1)
    operation_repo.bulk_insert(hid, r.items)
    history_repo.update_status(hid, "done", r.moved, 0)

    # Occupy the original location with a file that MUST survive the undo.
    (src / "a.jpg").write_bytes(b"IMPORTANT-KEEP")

    ops = operation_repo.list_by_history(hid)
    execute_undo(ops)

    _assert((src / "a.jpg").read_bytes() == b"IMPORTANT-KEEP", "original file NOT overwritten")
    _assert((src / "a (1).jpg").exists(), "restored file renamed with suffix instead of overwrite")
    _assert(not (src / "图片" / "a.jpg").exists(), "moved copy was relocated out of category folder")


# --------------------------------------------------------------------------- #
# P0-4: scanner skips system / hidden files and refuses the app data dir
# --------------------------------------------------------------------------- #
def test_scanner_protection():
    print("[P0-4] 扫描保护（系统文件 / 隐藏文件 / 应用数据目录）")
    src = _make_source(["photo.jpg", "desktop.ini", "thumbs.db", "ehthumbs.db"])

    hidden = src / ".hidden_cfg"
    hidden.write_bytes(b"x")
    hid_set = False
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.kernel32.SetFileAttributesW(str(hidden), 0x2)  # hidden
            hid_set = True
        except Exception:  # noqa: BLE001
            hid_set = False

    res = scan(src, mode="type")
    names = {f.name for f in res.files}
    _assert("photo.jpg" in names, "normal file is scanned")
    _assert("desktop.ini" not in names, "desktop.ini skipped")
    _assert("thumbs.db" not in names, "thumbs.db skipped")
    _assert("ehthumbs.db" not in names, "ehthumbs.db skipped")
    if hid_set:
        _assert(".hidden_cfg" not in names, "hidden file skipped")
    else:
        print("  (skip) hidden-file check unavailable on this platform")

    # App data directory must be refused with a clear error.
    ad = database.data_dir()
    raised = False
    try:
        scan(ad, mode="type")
    except ValueError:
        raised = True
    _assert(raised, "scanning the app data directory raises ValueError")


def main():
    database.init_db()
    test_interrupt_recovery()
    test_partial_undo_no_false_success()
    test_undo_no_overwrite()
    test_scanner_protection()
    print("\nALL P0 SECURITY TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(_TMP_HOME, ignore_errors=True)
