"""Phase-3 P1 reliability tests (no UI, Qt-free).

Run:  PYTHONPATH=src python tests/test_reliability.py

Covers P1-1 (WAL / busy_timeout / concurrency), P1-2 (batch ops),
P1-3 (scan de-duplication across modes), P1-4 (structured failure records),
P1-6 (friendly error mapping).
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

_TMP_HOME = tempfile.mkdtemp(prefix="dc_rel_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core import organize, plan, scan, move_items  # noqa: E402
from core.organizer import PlanItem  # noqa: E402
from data import database  # noqa: E402
from data import history_repo, operation_repo  # noqa: E402
from utils.errors import friendly_message  # noqa: E402


def _assert(cond: bool, msg: str):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("  ok:", msg)


def _make_source(names, base=None) -> Path:
    src = base or Path(tempfile.mkdtemp(prefix="dc_rel_src_"))
    for n in names:
        (src / n).write_bytes(b"data")
    return src


# --------------------------------------------------------------------------- #
# P1-1: SQLite WAL + busy_timeout
# --------------------------------------------------------------------------- #
def test_wal_and_busytimeout():
    print("[P1-1] WAL / busy_timeout")
    database.init_db()
    conn = database.get_connection()
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        _assert(mode.lower() == "wal", f"journal_mode is WAL (got {mode})")
        bt = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        _assert(bt >= 5000, f"busy_timeout >= 5000 (got {bt})")
    finally:
        conn.close()


def test_concurrent_connections():
    print("[P1-1] 并发读写不立即失败")
    database.init_db()
    c1 = database.get_connection()
    c2 = database.get_connection()
    try:
        # c1 writes but does not commit yet; c2 must be able to read (WAL) or
        # at least wait via busy_timeout instead of raising immediately.
        c1.execute("INSERT INTO settings(key, value) VALUES('k_rel', 'v')")
        rows = c2.execute("SELECT * FROM settings").fetchall()
        c1.commit()
        rows = c2.execute("SELECT * FROM settings").fetchall()
        _assert(any(r["key"] == "k_rel" for r in rows), "second connection sees committed row")
    finally:
        c1.close()
        c2.close()


# --------------------------------------------------------------------------- #
# P1-2: batch operations
# --------------------------------------------------------------------------- #
def test_batch_status_update():
    print("[P1-2] 批量结算 moved/failed")
    src = _make_source(["a.jpg", "b.jpg", "c.pdf"])
    items = plan(src, mode="type")
    _assert(len(items) == 3, "3 planned")
    hid = history_repo.create(str(src), "type", 3)
    operation_repo.bulk_insert_pending(hid, items)
    moved = {str(items[0].target)}
    failed = {str(items[1].target), str(items[2].target)}
    operation_repo.update_statuses_by_target(hid, moved, failed)
    ops = operation_repo.list_by_history(hid)
    status = {op["file_name"]: op["status"] for op in ops}
    _assert(status["a.jpg"] == "moved", "a.jpg -> moved")
    _assert(status["b.jpg"] == "failed", "b.jpg -> failed")
    _assert(status["c.pdf"] == "failed", "c.pdf -> failed")


# --------------------------------------------------------------------------- #
# P1-3: scan de-duplication across modes
# --------------------------------------------------------------------------- #
def test_scan_no_duplicates():
    print("[P1-3] 单轮扫描无重复")
    src = _make_source(["a.jpg", "b.pdf", "c.mp3"])
    res = scan(src, mode="type")
    _assert(res.total == 3, "3 files")
    _assert(len({str(f) for f in res.files}) == 3, "all source paths unique")


def test_recursive_no_double_count():
    print("[P1-3] 递归子目录不重复计数")
    src = _make_source(["a.jpg"])
    sub = src / "docs"
    sub.mkdir()
    (sub / "x.pdf").write_bytes(b"1")
    res = scan(src, mode="type", recursive=True)
    _assert(res.total == 2, "top file + nested file = 2 (no dup)")


def test_modes_do_not_pollute_each_other():
    print("[P1-3] 跨模式不互相污染")
    # type -> date
    src = _make_source(["a.jpg", "b.pdf"])
    organize(src, mode="type")  # creates 图片/ 文档/ ...
    res = scan(src, mode="date", recursive=True)
    _assert(res.total == 0, "type-output folders skipped by date scan")
    # date -> type
    src2 = _make_source(["c.pdf"])
    organize(src2, mode="date")  # creates 2026-08/
    res2 = scan(src2, mode="type", recursive=True)
    _assert(res2.total == 0, "date-output folder skipped by type scan")


def test_symlink_not_wrongly_dropped():
    print("[P1-3] 符号链接不被去重误删")
    src = _make_source(["real.jpg"])
    try:
        os.symlink(str(src / "real.jpg"), str(src / "link.jpg"))
    except (OSError, NotImplementedError, AttributeError):
        print("  (skip) symlink creation unavailable on this platform")
        return
    res = scan(src, mode="type")
    names = {f.name for f in res.files}
    _assert("real.jpg" in names, "real file scanned")
    _assert("link.jpg" in names, "symlink entry kept (not merged with target)")


# --------------------------------------------------------------------------- #
# P1-4: structured failure records
# --------------------------------------------------------------------------- #
def test_failure_details_recorded():
    print("[P1-4] 失败记录含结构化字段")
    src = _make_source(["a.jpg"])
    blocker = src / "blocker"
    blocker.write_bytes(b"x")  # a file where the target's parent should be
    item = PlanItem(source=src / "a.jpg", target=blocker / "a.jpg", category="图片")
    r = move_items([item])
    _assert(r.failed == 1, "1 move failed")
    _assert(len(r.failed_details) == 1, "one structured failure recorded")
    d = r.failed_details[0]
    for key in ("source", "target", "operation", "error_type", "error_message", "timestamp"):
        _assert(key in d, f"failure detail has '{key}'")


# --------------------------------------------------------------------------- #
# P1-6: friendly error mapping
# --------------------------------------------------------------------------- #
def test_friendly_messages():
    print("[P1-6] 友好异常映射")
    _assert("权限" in friendly_message(PermissionError("denied")), "PermissionError -> 权限提示")
    _assert("找不到" in friendly_message(FileNotFoundError("no")), "FileNotFound -> 找不到")
    import sqlite3
    _assert("忙" in friendly_message(sqlite3.OperationalError("database is locked")), "locked -> 忙")
    _assert("日志" in friendly_message(RuntimeError("boom")), "unknown -> 日志兜底")


def main():
    test_wal_and_busytimeout()
    test_concurrent_connections()
    test_batch_status_update()
    test_scan_no_duplicates()
    test_recursive_no_double_count()
    test_modes_do_not_pollute_each_other()
    test_symlink_not_wrongly_dropped()
    test_failure_details_recorded()
    test_friendly_messages()
    print("\nALL P1 RELIABILITY TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(_TMP_HOME, ignore_errors=True)
