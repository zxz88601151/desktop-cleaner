"""End-to-end logic test for core + data layers (no UI).

Run:  PYTHONPATH=src python tests/test_core.py
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Isolate the SQLite DB into a temp dir via env override.
_TMP_HOME = tempfile.mkdtemp(prefix="dc_test_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core import organize, scan, execute_undo  # noqa: E402
from data import database  # noqa: E402
from data import history_repo, operation_repo  # noqa: E402


def _make_source() -> Path:
    src = Path(tempfile.mkdtemp(prefix="dc_src_"))
    files = {
        "photo.jpg": b"img",
        "logo.png": b"img",
        "report.pdf": b"doc",
        "notes.docx": b"doc",
        "clip.mp4": b"vid",
        "song.mp3": b"aud",
        "archive.zip": b"zip",
        "script.py": b"code",
        "setup.exe": b"exe",
        "readme": b"noext",
    }
    for name, content in files.items():
        (src / name).write_bytes(content)
    # a nested file (only moved when recursive=True)
    sub = src / "projects"
    sub.mkdir()
    (sub / "deep.txt").write_bytes(b"nested")
    return src


def _assert(cond: bool, msg: str):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("  ok:", msg)


def main():
    database.init_db()
    src = _make_source()

    print("[1] scan (type, non-recursive)")
    res = scan(src, mode="type", recursive=False)
    _assert(res.total == 10, f"10 top-level files found (got {res.total})")
    _assert(res.by_category.get("图片") == 2, "2 images")
    _assert(res.by_category.get("文档") == 2, "2 documents")
    _assert("其他" in res.by_category, "extension-less file -> 其他")

    print("[2] organize (type)")
    r = organize(src, mode="type", recursive=False)
    _assert(r.total == 10, f"planned 10 (got {r.total})")
    _assert(r.moved == 10, f"moved 10 (got {r.moved})")
    _assert(r.failed == 0, "no failures")
    _assert(not (src / "photo.jpg").exists(), "source photo.jpg gone after move")
    _assert((src / "图片" / "photo.jpg").exists(), "photo.jpg in 图片/")
    _assert((src / "projects" / "deep.txt").exists(), "nested file untouched (non-recursive)")

    print("[3] persist history + operations")
    hid = history_repo.create(str(src), "type", r.total)
    operation_repo.bulk_insert(hid, r.items)
    history_repo.update_status(hid, "done", r.moved, 0)
    ops = operation_repo.list_by_history(hid)
    _assert(len(ops) == 10, f"10 operations recorded (got {len(ops)})")

    print("[4] re-scan should NOT re-process organized folders")
    res2 = scan(src, mode="type", recursive=False)
    _assert(res2.total == 0, f"0 files after organize (got {res2.total})")

    print("[5] undo")
    hist = history_repo.latest_done()
    _assert(hist is not None and hist["id"] == hid, "latest done history found")
    ops = operation_repo.list_by_history(hid)
    ur = execute_undo(ops)
    _assert(ur.moved == 10, f"10 files restored (got {ur.moved})")
    _assert((src / "photo.jpg").exists(), "photo.jpg restored to source")
    _assert(not (src / "图片" / "photo.jpg").exists(), "moved copy removed")
    history_repo.update_status(hid, "undone")
    _assert(history_repo.get(hid)["status"] == "undone", "history marked undone")

    print("[6] collision rename")
    src2 = Path(tempfile.mkdtemp(prefix="dc_collide_"))
    (src2 / "a.jpg").write_bytes(b"1")
    (src2 / "图片").mkdir()
    (src2 / "图片" / "a.jpg").write_bytes(b"existing")
    r2 = organize(src2, mode="type", recursive=False)
    _assert(r2.moved == 1, "collision case moved 1")
    _assert((src2 / "图片" / "a (1).jpg").exists(), "collision renamed to 'a (1).jpg' (Windows style)")
    _assert((src2 / "图片" / "a.jpg").exists(), "original kept")

    print("[7] date mode")
    src3 = Path(tempfile.mkdtemp(prefix="dc_date_"))
    (src3 / "x.pdf").write_bytes(b"d")
    rd = organize(src3, mode="date", recursive=False)
    _assert(rd.moved == 1, "date mode moved 1")
    date_folders = [p for p in src3.iterdir() if p.is_dir() and len(p.name) == 7]
    _assert(len(date_folders) == 1, "one YYYY-MM folder created")

    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(_TMP_HOME, ignore_errors=True)
