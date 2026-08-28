"""V1.1.0 RC — combined-path (Chinese + space) and deep long-path real-FS E2E.

Drives the SAME frozen core modules the shipped EXE bundles, against REAL
folders whose names contain BOTH Chinese characters AND spaces (the gap that
AR-1 closed), plus a best-effort deep >260-char path. No GUI, Qt-free.

Run:  PYTHONPATH=src python tests/test_combined_path_v11.py
"""
import os
import sys
import tempfile
from pathlib import Path

_TMP_HOME = tempfile.mkdtemp(prefix="dc_v11_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core import plan, move_items, execute_undo  # noqa: E402
from data import database, history_repo, operation_repo  # noqa: E402
from utils.paths import win_long  # noqa: E402

database.init_db()  # ensure schema exists in isolated temp HOME


def _assert(cond, msg):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("  ok:", msg)


def _touch(p: Path, content=b"x"):
    os.makedirs(win_long(p.parent), exist_ok=True)
    Path(win_long(p)).write_bytes(content)


def _organize_flow(src, mode="type", recursive=False):
    items = plan(src, mode=mode, recursive=recursive)
    hid = history_repo.create(str(src), mode, len(items))
    operation_repo.bulk_insert_pending(hid, items)
    r = move_items(items)
    moved = {str(it.target) for it in r.items}
    failed = {str(it.target) for it in r.failed_items}
    operation_repo.update_statuses_by_target(hid, moved, failed)
    history_repo.update_status(hid, "done", r.moved, r.skipped)
    return hid, r


def _undo_flow(hid):
    ops = operation_repo.list_by_history(hid)
    result = execute_undo(ops)
    operation_repo.apply_undo_result(hid, result)
    return result


# --------------------------------------------------------------------------- #
# V11-A 中文 + 空格 组合路径
# --------------------------------------------------------------------------- #
def test_combined_chinese_space():
    print("[V11-A] 中文 + 空格 组合路径 organize + undo")
    # source folder name contains BOTH Chinese chars AND a space
    src = Path(tempfile.mkdtemp(prefix="测试 Folder "))
    print("  src =", src)
    for n in ["照片.jpg", "报告.pdf", "音乐.mp3", "压缩包.zip", "脚本.py"]:
        _touch(src / n)
    hid, r = _organize_flow(src, "type")
    _assert(r.moved == 5, f"5 files moved under Chinese+space dir (got {r.moved})")
    _assert((src / "图片" / "照片.jpg").exists(), "照片.jpg -> 图片/")
    _assert((src / "文档" / "报告.pdf").exists(), "报告.pdf -> 文档/")
    _assert((src / "音频" / "音乐.mp3").exists(), "音乐.mp3 -> 音频/")
    _assert((src / "压缩包" / "压缩包.zip").exists(), "压缩包.zip -> 压缩包/")
    _assert((src / "代码" / "脚本.py").exists(), "脚本.py -> 代码/")
    ops = operation_repo.list_by_history(hid)
    _assert(all(o["status"] == "moved" for o in ops), "all ops status=moved")
    # undo restores to original Chinese+space path
    result = _undo_flow(hid)
    _assert(result.moved == 5, f"5 restored (got {result.moved})")
    _assert((src / "照片.jpg").exists(), "照片.jpg restored to source root")
    _assert(not (src / "图片" / "照片.jpg").exists(), "moved copy removed after undo")
    print("  [V11-A] PASS")


# --------------------------------------------------------------------------- #
# V11-B 深层长路径 best-effort (>260 chars)
# --------------------------------------------------------------------------- #
def test_deep_long_path():
    print("[V11-B] 深层长路径 best-effort organize")
    # build a nested path well beyond 260 chars using Chinese + space segments
    base = Path(tempfile.mkdtemp(prefix="deep "))
    cur = base
    seg = "长路径测试目录"
    for _ in range(12):
        cur = cur / seg
    os.makedirs(win_long(cur), exist_ok=True)
    _touch(cur / "data.txt")
    full_len = len(str(cur / "data.txt"))
    print("  full path length =", full_len)
    hid, r = _organize_flow(cur, "type", recursive=False)
    if full_len > 260:
        # best-effort: either succeeded or recorded as failure, never crash
        _assert(r.moved + len(r.failed_items) == 1, "handled 1 item without crash")
        print("  [V11-B] PASS (best-effort, no crash on >260 path)")
    else:
        _assert(r.moved == 1, "1 file moved on short-enough path")
        print("  [V11-B] PASS")


if __name__ == "__main__":
    test_combined_chinese_space()
    test_deep_long_path()
    print("\nALL V1.1.0 COMBINED-PATH E2E SCENARIOS PASSED (real core modules + real filesystem)")
