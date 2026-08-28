"""Feature 2 (V1.1): home dashboard stat cards.

Tests that DashboardWidget.refresh() reads aggregated stats from the
history table and renders them into the three stat cards.

Run:  PYTHONPATH=src QT_QPA_PLATFORM=offscreen python tests/test_dashboard.py
"""
import os
import sys
import tempfile
import shutil

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_TMP_HOME = tempfile.mkdtemp(prefix="dc_test_dash_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from data import database, history_repo  # noqa: E402
from ui.dashboard import DashboardWidget  # noqa: E402

app = QApplication.instance() or QApplication(sys.argv)


def _assert(cond: bool, msg: str):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("  ok:", msg)


def _card_value(dash: DashboardWidget, key: str) -> str:
    return dash._cards[key]._value.text()


def main():
    database.init_db()

    print("[1] empty history -> zeros / dash")
    dash = DashboardWidget()
    dash.refresh()
    _assert(_card_value(dash, "total") == "0", "total files = 0")
    _assert(_card_value(dash, "runs") == "0", "runs = 0")
    _assert(_card_value(dash, "last") == "—", "last run = —")

    print("[2] two done runs are aggregated")
    history_repo.create("/tmp/a", "type", 0)
    history_repo.update_status(1, "done", 3, 0)
    history_repo.create("/tmp/b", "type", 0)
    history_repo.update_status(2, "done", 5, 0)
    dash.refresh()
    _assert(_card_value(dash, "total") == "8", f"total files = 8 (got {_card_value(dash, 'total')})")
    _assert(_card_value(dash, "runs") == "2", f"runs = 2 (got {_card_value(dash, 'runs')})")
    _assert(len(_card_value(dash, "last")) == 10, "last run shows a YYYY-MM-DD date")

    print("[3] undone runs still count toward runs total")
    history_repo.update_status(1, "undone")
    dash.refresh()
    _assert(_card_value(dash, "runs") == "2", "undone run still counted in runs")
    _assert(_card_value(dash, "total") == "5", "undone run excluded from total files")

    print("\nDASHBOARD TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(_TMP_HOME, ignore_errors=True)
