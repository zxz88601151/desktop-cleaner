"""Theme system smoke test (UI refactor, V1.2).

Validates that both themes render a complete (token-substituted) stylesheet,
that the manager toggles/persists, and that dialogs keep their test contracts
under the new tokenised QSS.
"""
import os
import re
import sys
import tempfile
import shutil

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_TMP_HOME = tempfile.mkdtemp(prefix="dc_test_theme_")
os.environ["DESKTOP_CLEANER_HOME"] = _TMP_HOME

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PySide6.QtWidgets import QApplication, QPushButton, QLabel  # noqa: E402

from data import database  # noqa: E402
from data import settings_repo  # noqa: E402
from ui import themes, theme_manager  # noqa: E402

_TOKEN = re.compile(r"\{\{|\}\}|\{[a-zA-Z_][a-zA-Z0-9_]*\}")


def _assert(cond, msg):
    if not cond:
        raise AssertionError("FAIL: " + msg)
    print("  ok:", msg)


def main():
    database.init_db()
    app = QApplication.instance() or QApplication(sys.argv)

    print("[1] both themes render a complete stylesheet")
    for name in ("light", "dark"):
        ss = themes.build_stylesheet(name)
        bad = _TOKEN.findall(ss)
        _assert(not bad, f"{name} has no unresolved tokens ({bad[:3]})")
        _assert("QPushButton#primary" in ss, f"{name} styles primary button")

    print("[2] ThemeManager toggles and persists")
    tm = theme_manager.ThemeManager.instance()
    tm.set_theme("light")
    _assert(tm.theme == "light", "starts light")
    tm.set_theme("dark")
    _assert(tm.theme == "dark", "switched to dark")
    _assert(settings_repo.get("theme") == "dark", "theme persisted to settings")
    tm.toggle()
    _assert(tm.theme == "light", "toggle back to light")

    print("[3] shadow colour differs by theme")
    light_sh = themes.shadow_color("light").name()
    dark_sh = themes.shadow_color("dark").name()
    _assert(light_sh != dark_sh, f"shadow differs ({light_sh} vs {dark_sh})")

    print("[4] dialog contracts preserved under token QSS")
    from ui.welcome import WelcomeDialog
    from ui.preview_report import PreviewReportDialog
    from core import plan, summarize_plan
    from pathlib import Path

    d1 = WelcomeDialog()
    # P2-3 added two safety bullets (预览 / 不覆盖), so there are now 6.
    _assert(len(d1.findChildren(QLabel, "welcome-bullet")) == 6, "welcome has 6 bullets")
    _assert(any(b.text() == "开始使用" for b in d1.findChildren(QPushButton)), "welcome 开始使用")

    src = Path(tempfile.mkdtemp())
    for n in ("a.jpg", "b.pdf", "c.mp4"):
        (src / n).write_bytes(b"x")
    rep = summarize_plan(plan(src, mode="type"), str(src))
    d3 = PreviewReportDialog(rep)
    _assert(any(b.text() == "开始整理" for b in d3.findChildren(QPushButton)), "preview 开始整理")
    _assert(d3.findChild(QLabel, "report-warn") is not None, "preview 不会删除 note")

    print("\nTHEME TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(_TMP_HOME, ignore_errors=True)
