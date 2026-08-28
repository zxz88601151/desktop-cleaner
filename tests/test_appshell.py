"""App Shell + full business-flow smoke test (full implementation).

Validates:
- AppShell builds and routes to every page without error.
- Theme toggle still works under the tokenised QSS.
- The real 4-step organize task (create -> organize -> bulk_insert ->
  update_status) moves files and records history + operations.
- The 5-step undo task restores files and flips status to "undone".
- Premium controls (ToggleSwitch / Segmented) emit correctly.

Run:  PYTHONPATH=src QT_QPA_PLATFORM=offscreen python tests/test_appshell.py
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_TMP_HOME = tempfile.mkdtemp(prefix="dc_test_appshell_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from data import database, history_repo, operation_repo, settings_repo  # noqa: E402
from ui.app_shell import AppShell  # noqa: E402
from ui.pages.organize_page import OrganizePage  # noqa: E402
from ui.pages.history_page import HistoryPage  # noqa: E402
from ui.pages.dashboard_page import DashboardPage  # noqa: E402
from ui.undo import ConfirmUndoDialog, run_undo  # noqa: E402
from ui.widgets.controls import Segmented, ToggleSwitch  # noqa: E402
from ui.theme_manager import ThemeManager  # noqa: E402


def _assert(cond, msg):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("  ok:", msg)


def _no_op(*_a):
    pass


def _make_source() -> str:
    src = tempfile.mkdtemp(prefix="dc_src_")
    for name, content in {
        "photo.jpg": b"img", "logo.png": b"img", "report.pdf": b"doc",
        "clip.mp4": b"vid", "song.mp3": b"aud", "archive.zip": b"zip",
        "script.py": b"code", "setup.exe": b"exe",
    }.items():
        (Path(src) / name).write_bytes(content)  # type: ignore[name-defined]
    return src


def main():
    database.init_db()
    # skip the first-launch welcome dialog so the shell builds headlessly
    settings_repo.set("first_launch_completed", 1)
    app = QApplication.instance() or QApplication(sys.argv)

    print("[1] AppShell builds and routes to every page")
    shell = AppShell()
    for pid in ("home", "organize", "custom", "history", "settings"):
        shell._route(pid)
        _assert(shell.stack.currentWidget() is shell._pages[pid], f"routed to {pid}")
        page = shell._pages[pid]
        enter = getattr(page, "on_enter", None)
        if callable(enter):
            enter()

    print("[2] theme toggle works under tokenised QSS")
    tm = ThemeManager.instance()
    tm.set_theme("light")
    _assert(tm.theme == "light", "starts light")
    tm.toggle()
    _assert(tm.theme == "dark", "toggled to dark")
    tm.set_theme("light")

    print("[3] controls emit correctly")
    seg = Segmented([("type", "按类型"), ("date", "按日期")])
    got = {}
    seg.selected.connect(lambda v: got.setdefault("v", v))
    seg.set_value("date")
    _assert(seg.value() == "date", "segmented value = date")
    _assert(got.get("v") == "date", "segmented emitted 'date'")
    tog = ToggleSwitch(False)
    states = []
    tog.toggled.connect(lambda b: states.append(b))
    tog.set_on(True)
    _assert(tog.is_on() and states == [True], "toggle switched on")

    print("[4] real 4-step organize task moves files + records history")
    src = _make_source()
    payload = OrganizePage._task_organize(src, "type", False, _no_op, _no_op)
    hid = payload["hid"]
    result = payload["result"]
    _assert(result.moved == 8, f"moved 8 files (got {result.moved})")
    rec = history_repo.get(hid)
    _assert(rec is not None and rec["status"] == "done", "history marked done")
    _assert(rec["organized_files"] == 8, "history recorded 8 organized files")
    ops = operation_repo.list_by_history(hid)
    _assert(len(ops) == 8, f"8 operations recorded (got {len(ops)})")
    # files actually moved into category folders
    moved = any((Path(src) / "图片" / "photo.jpg").exists() for _ in [0])
    _assert(moved, "photo.jpg moved into 图片 folder")
    _assert(not (Path(src) / "photo.jpg").exists(), "source photo.jpg removed")

    print("[5] real 5-step undo task restores files")
    undo_payload = run_undo(hid, _no_op, _no_op)
    _assert(undo_payload["result"].moved == 8, "undo moved 8 back")
    rec2 = history_repo.get(hid)
    _assert(rec2["status"] == "undone", "history marked undone")
    _assert((Path(src) / "photo.jpg").exists(), "photo.jpg restored to source")
    _assert(not (Path(src) / "图片").exists(), "empty 图片 folder cleaned up")

    print("[6] one-click undo UI hooks are wired")
    org = OrganizePage()
    _assert(
        org._done.findChild(QPushButton, "undo-cta") is not None,
        "organize done-stage has undo button",
    )
    dash = DashboardPage()
    _assert(
        dash.findChild(QPushButton, "undo-cta") is not None,
        "dashboard has one-click undo button",
    )
    dlg = ConfirmUndoDialog(1, 8, src)
    _assert(
        any(b.text() == "还原" for b in dlg.findChildren(QPushButton)),
        "confirm dialog has 还原 button",
    )

    print("\nAPPSHELL TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(_TMP_HOME, ignore_errors=True)
