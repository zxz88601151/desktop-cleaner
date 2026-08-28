"""UI-1.3 Phase 1.5 — real-render screenshots at 100 / 125 / 150% DPI.

Mirrors tests/_shots.py (renders the actual Qt widget tree with the real
theme + CJK fonts). The offscreen QPA reports DPR=1 and ignores QT_SCALE_FACTOR,
so to evidence high-DPI output we rasterize the real widget tree with a scaled
QPainter — exactly what a native Windows session does at 125% / 150% (logical
layout stays identical, physical pixels grow).

Run once per scale factor:
    QT_QPA_PLATFORM=offscreen DC_SCALE=1.0  python tests/_shots_15.py
    QT_QPA_PLATFORM=offscreen DC_SCALE=1.25 python tests/_shots_15.py
    QT_QPA_PLATFORM=offscreen DC_SCALE=1.5  python tests/_shots_15.py

Output: docs/ui-1.3-phase1-5/<scale>/<name>.png
"""
import sys, os, tempfile, time, traceback
sys.path.insert(0, "src")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
SCALE = float(os.environ.get("DC_SCALE", "1.0"))

home = tempfile.mkdtemp()
os.environ["DESKTOP_CLEANER_HOME"] = home

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                   "docs", "ui-1.3-phase1-5", f"{int(SCALE*100)}")
os.makedirs(OUT, exist_ok=True)
_LOG = os.path.join(OUT, "_shots_log.txt")


def _log(msg):
    with open(_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


open(_LOG, "w", encoding="utf-8").close()
try:
    from PySide6.QtWidgets import QApplication, QWidget
    from PySide6.QtGui import (QPixmap, QColor, QFontDatabase, QFont, QPainter)
    from PySide6.QtCore import Qt, QPoint
    from data.database import init_db
    from data import settings_repo, history_repo
    from ui.theme_manager import ThemeManager
    from ui import theme

    init_db()
    settings_repo.set("first_launch_completed", 1)
    _hid = history_repo.create(home, "type", 0)
    history_repo.update_status(_hid, "done", 8, 0)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    for f in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc"]:
        QFontDatabase.addApplicationFont(f)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    theme.themes.FONT_FAMILY = '"Microsoft YaHei UI", "Segoe UI", sans-serif'
    theme.themes.MONO_FAMILY = '"Consolas", "Courier New", monospace'
    ThemeManager.instance().apply(app)

    from ui.app_shell import AppShell
    w = AppShell()
    w.resize(1180, 748)
    w.show()
    app.processEvents()
    time.sleep(0.2)

    surface = QColor("#F7F8FC")

    def render_widget(widget, name):
        pw, ph = int(widget.width() * SCALE), int(widget.height() * SCALE)
        pix = QPixmap(pw, ph)
        pix.fill(surface)
        p = QPainter(pix)
        p.scale(SCALE, SCALE)
        widget.render(p, QPoint())
        p.end()
        path = os.path.join(OUT, f"{name}.png")
        pix.save(path)
        _log(f"saved {name} -> {path} ({pw}x{ph} @scale{SCALE})")

    def shot(page_id, name, extra=None):
        if extra:
            extra()
        w._route(page_id)
        app.processEvents()
        time.sleep(0.15)
        render_widget(w, name)

    # Phase 1.5: 整理 is the default / Product Home landing route.
    shot("organize", "01_organize_default")
    shot("history", "02_history")

    def _show_done():
        org = w._pages["organize"]
        org._set_stage(org._done)

    shot("organize", "03_organize_done", extra=_show_done)
    shot("settings", "04_settings")
    shot("custom", "05_custom_registered")

    from ui.about import AboutDialog
    dlg = AboutDialog(w)
    dlg.show()
    app.processEvents()
    time.sleep(0.1)
    render_widget(dlg, "06_about_dialog")

    _log("DONE_SHOTS " + OUT + f" scale={SCALE}")
except Exception:
    _log("SHOTS ERROR:\n" + traceback.format_exc())
    raise
