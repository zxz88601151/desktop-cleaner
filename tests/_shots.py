import sys, os, tempfile, time, traceback
sys.path.insert(0, "src")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
home = tempfile.mkdtemp()
os.environ["DESKTOP_CLEANER_HOME"] = home

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "design", "shots")
os.makedirs(OUT, exist_ok=True)
_LOG = os.path.join(OUT, "_shots_log.txt")


def _log(msg):
    with open(_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


open(_LOG, "w", encoding="utf-8").close()
try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QPixmap, QColor, QFontDatabase, QFont
    from PySide6.QtCore import Qt
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

    def shot(page_id, name, extra=None):
        if extra:
            extra()
        w._route(page_id)
        app.processEvents()
        time.sleep(0.15)
        pix = QPixmap(w.size())
        pix.fill(surface)
        w.render(pix)
        path = os.path.join(OUT, f"{name}.png")
        pix.save(path)
        _log(f"saved {name} -> {path}")

    shot("home", "home")
    shot("organize", "organize")

    def _show_done():
        org = w._pages["organize"]
        org._set_stage(org._done)

    shot("organize", "organize_done", extra=_show_done)
    shot("custom", "custom")
    shot("history", "history")
    shot("settings", "settings")

    from ui.undo import ConfirmUndoDialog
    dlg = ConfirmUndoDialog(1, 8, home)
    dlg.show()
    app.processEvents()
    time.sleep(0.1)
    pix = QPixmap(dlg.size())
    pix.fill(surface)
    dlg.render(pix)
    dpath = os.path.join(OUT, "confirm_undo.png")
    pix.save(dpath)
    _log(f"saved confirm_undo -> {dpath}")

    _log("DONE_SHOTS " + OUT)
except Exception:
    _log("SHOTS ERROR:\n" + traceback.format_exc())
    raise
