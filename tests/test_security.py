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
from core.organizer import PlanItem, move_items, undo_plan  # noqa: E402
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


# --------------------------------------------------------------------------- #
# P0-5: move_items must never overwrite a file that exists at the target
# --------------------------------------------------------------------------- #
def test_move_never_overwrites_existing_target():
    """Audit 2026-10-16: shutil.move's copy fallback silently OVERWRITES an
    existing destination. A file created at the planned target between the
    preview and the execute click was destroyed and the move reported as a
    success. The engine must record a failure instead — never lose bytes."""
    print("[P0-5] 目标碰撞保护（移动不覆盖）")
    root = Path(tempfile.mkdtemp(prefix="dc_sec_ow_"))
    (root / "incoming.txt").write_bytes(b"incoming")
    (root / "文档").mkdir()
    victim = root / "文档" / "incoming.txt"
    victim.write_bytes(b"ORIGINAL-PRECIOUS")  # appeared after planning

    items = [
        PlanItem(source=root / "incoming.txt", target=victim, category="文档")
    ]
    res = move_items(items)

    _assert(res.failed == 1, "colliding move is recorded as a failure")
    _assert(res.moved == 0, "colliding move is not reported as success")
    _assert(
        victim.read_bytes() == b"ORIGINAL-PRECIOUS",
        "the file already at the target is intact",
    )
    _assert((root / "incoming.txt").exists(), "the source file is untouched")


def test_copy_no_overwrite_helper():
    """The copy fallback used by shutil.move (cross-volume moves) must also
    refuse an existing destination — that fallback is exactly where the old
    silent overwrite happened."""
    print("[P0-5b] copy 回退路径不覆盖")
    from core.organizer import _copy_no_overwrite

    base = Path(tempfile.mkdtemp(prefix="dc_sec_cpy_"))
    src = base / "src.bin"
    src.write_bytes(b"payload")
    dst = base / "dst.bin"
    dst.write_bytes(b"DO-NOT-DESTROY")

    raised = False
    try:
        _copy_no_overwrite(str(src), str(dst))
    except FileExistsError:
        raised = True
    _assert(raised, "copy into an existing destination raises FileExistsError")
    _assert(dst.read_bytes() == b"DO-NOT-DESTROY", "existing destination intact")

    free = base / "free.bin"
    _copy_no_overwrite(str(src), str(free))
    _assert(free.read_bytes() == b"payload", "copy to a free destination works")


# --------------------------------------------------------------------------- #
# P0-6: undo plan reserves restore targets (two restores never collide)
# --------------------------------------------------------------------------- #
def test_undo_restore_collision_no_data_loss():
    """Audit 2026-10-16: undo_plan had no `reserved` set, so two restores whose
    original spots collide after a "(1)" rename shared one destination — the
    second move overwrote the first and was reported as success (moved=2,
    failed=0) while one file's content was destroyed."""
    print("[P0-6] 撤销目标预留（双还原不碰撞）")
    src = _make_source([])
    (src / "x.txt").write_bytes(b"CONTENT-OF-x")
    (src / "x (1).txt").write_bytes(b"CONTENT-OF-x1")

    r = organize(src, mode="type")
    _assert(r.moved == 2, "both files organized")
    hid = _new_history(src, "type", 2)
    operation_repo.bulk_insert(hid, r.items)
    history_repo.update_status(hid, "done", 2, 0)

    # The user re-creates x.txt at the original spot while the files are
    # organized; op1's restore is renamed to "x (1).txt", colliding with op2's.
    (src / "x.txt").write_bytes(b"USER-RECREATED")

    ops = operation_repo.list_by_history(hid)
    plan_targets = [str(i.target) for i in undo_plan(ops)]
    _assert(len(plan_targets) == len(set(plan_targets)),
            "undo plan hands out unique restore targets")

    res = execute_undo(ops)
    _assert(res.failed == 0, "every restore succeeds")
    contents = sorted(p.read_bytes() for p in src.glob("*.txt"))
    _assert(
        contents == sorted(
            [b"CONTENT-OF-x", b"CONTENT-OF-x1", b"USER-RECREATED"]
        ),
        "all three file contents survive (no silent overwrite)",
    )


def main():
    database.init_db()
    test_interrupt_recovery()
    test_partial_undo_no_false_success()
    test_undo_no_overwrite()
    test_move_never_overwrites_existing_target()
    test_copy_no_overwrite_helper()
    test_undo_restore_collision_no_data_loss()
    test_scanner_protection()
    print("\nALL P0 SECURITY TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(_TMP_HOME, ignore_errors=True)
