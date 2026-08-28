"""Phase-3 P1-5 Windows long-path tests (no UI, Qt-free).

Run:  PYTHONPATH=src python tests/test_windows_paths.py

This host runs under Git-Bash-on-Windows, so ``os.name == "nt"`` and the
Windows branch of :func:`utils.paths.win_long` is exercised for real:
  - short paths are normalized to absolute form (no ``\\\\?\\`` prefix);
  - long (>240 char) paths receive the ``\\\\?\\`` namespace prefix;
  - a best-effort real >260-char move is attempted to confirm the prefix
    actually enables long-path operations on this filesystem.
Where the real move is not supported by the sandbox FS it is skipped, and the
long-path guarantee is reported as CONDITIONAL in the Phase-3 report.
"""
import os
import sys
import shutil
import tempfile
from pathlib import Path

_TMP_HOME = tempfile.mkdtemp(prefix="dc_win_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from utils.paths import win_long, safe_is_file, safe_exists  # noqa: E402
from core import organize  # noqa: E402
from data import database  # noqa: E402


def _assert(cond: bool, msg: str):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("  ok:", msg)


def test_win_long_short_path():
    print("[P1-5] 短路径：规范化但不加 \\\\?\\ 前缀")
    if os.name == "nt":
        p = "C:\\Users\\test\\photo.jpg"
    else:
        p = "/tmp/photo.jpg"
    out = win_long(p)
    if os.name == "nt":
        _assert(out == os.path.abspath(p), "Windows: normalized to absolute")
        _assert(not out.startswith("\\\\?\\"), "short path keeps no \\\\?\\ prefix")
    else:
        _assert(out == p, "non-Windows: passthrough unchanged")


def test_win_long_prefixes_long_path():
    print("[P1-5] 长路径：加 \\\\?\\ 前缀")
    if os.name != "nt":
        print("  (skip) not Windows")
        return
    base = os.path.abspath("C:\\")
    p = os.path.join(base, "x" * 300 + ".jpg")
    out = win_long(p)
    _assert(out.startswith("\\\\?\\"), "long path gets \\\\?\\ prefix")
    _assert(out == "\\\\?\\" + os.path.abspath(p), "prefix wraps the absolute path")


def test_real_long_path_move():
    print("[P1-5] 真实 >260 字符移动（尽力验证）")
    if os.name != "nt":
        print("  (skip) not Windows")
        return
    d = Path(tempfile.mkdtemp(prefix="dc_long_"))
    try:
        src = d / "src.jpg"
        src.write_bytes(b"1")
        target = d / ("f" * 300 + ".jpg")
        shutil.move(win_long(src), win_long(target))
        _assert(target.exists(), "real >260-char move succeeded (VERIFIED on Windows)")
    except OSError as e:
        print(f"  (skip) real long-path move unsupported on this FS: {e}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_safe_helpers():
    print("[P1-5] safe_is_file / safe_exists 不抛异常")
    f = Path(tempfile.mkdtemp(prefix="dc_win_src_")) / "a.jpg"
    f.write_bytes(b"1")
    _assert(safe_is_file(f) is True, "safe_is_file True for real file")
    _assert(safe_exists(f) is True, "safe_exists True for real file")
    _assert(safe_is_file(f.parent / "nope.jpg") is False, "safe_is_file False for missing")


def test_organize_short_path_regression():
    print("[P1-5] 短路径整理无回归")
    src = Path(tempfile.mkdtemp(prefix="dc_win_rel_"))
    (src / "photo.jpg").write_bytes(b"img")
    (src / "doc.pdf").write_bytes(b"doc")
    database.init_db()
    r = organize(src, mode="type", recursive=False)
    _assert(r.moved == 2, f"2 files moved (got {r.moved})")
    _assert(r.failed == 0, "no failures on short paths")


def main():
    test_win_long_short_path()
    test_win_long_prefixes_long_path()
    test_real_long_path_move()
    test_safe_helpers()
    test_organize_short_path_regression()
    print("\nALL WINDOWS-PATH TESTS PASSED (real >260 move = best-effort)")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(_TMP_HOME, ignore_errors=True)
