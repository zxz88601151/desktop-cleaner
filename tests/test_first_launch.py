"""Feature 3 (V1.1): first-launch welcome dialog.

Tests:
- should_show_welcome() returns True before first launch, False after.
- WelcomeDialog.accept() records the first_launch_completed marker.
- The dialog builds and shows the four safety bullets + a start button.

Run:  PYTHONPATH=src QT_QPA_PLATFORM=offscreen python tests/test_first_launch.py
"""
import os
import sys
import tempfile
import shutil

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_TMP_HOME = tempfile.mkdtemp(prefix="dc_test_welcome_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PySide6.QtWidgets import QApplication, QLabel, QPushButton  # noqa: E402

from data import database, settings_repo  # noqa: E402
from ui.welcome import WelcomeDialog, should_show_welcome  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv)


def _assert(cond: bool, msg: str):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("  ok:", msg)


def main():
    database.init_db()

    print("[1] welcome shown on first launch")
    _assert(should_show_welcome() is True, "should_show_welcome True when never launched")

    print("[2] WelcomeDialog builds with bullets + start button")
    dlg = WelcomeDialog()
    bullets = dlg.findChildren(QLabel, "welcome-bullet")
    # P2-3 added two safety bullets (预览 / 不覆盖), so there are now 6.
    _assert(len(bullets) == 6, f"6 safety bullets (got {len(bullets)})")
    btns = dlg.findChildren(QPushButton)
    _assert(any(b.text() == "开始使用" for b in btns), "start button present")

    print("[3] accepting records the marker (never shown again)")
    dlg.accept()
    _assert(settings_repo.get("first_launch_completed") == "1", "marker written on accept")
    _assert(should_show_welcome() is False, "should_show_welcome False after accept")

    print("\nFIRST-LAUNCH TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(_TMP_HOME, ignore_errors=True)
