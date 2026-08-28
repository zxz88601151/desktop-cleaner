"""Desktop Cleaner - application entry point.

Run from source:
    python main.py

Build a Windows executable:
    see build.bat  (PyInstaller one-file)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the layered packages (core / data / ui / utils) importable.
APP_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_ROOT / "src"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from data.database import init_db
from data import operation_repo
from utils.logger import get_logger
from ui.app_shell import AppShell
from ui.theme_manager import ThemeManager

_log = get_logger("app")


def main():
    _log.info("APP START")
    # P2-5: enable high-DPI scaling so the UI stays crisp on 4K / scaled displays.
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    init_db()
    reconciled = operation_repo.reconcile_pending()  # P0-1 启动恢复
    if reconciled:
        _log.info("APP RECOVERED pending_ops=%d", reconciled)
    app = QApplication(sys.argv)
    app.setApplicationName("Desktop Cleaner")
    app.setApplicationDisplayName("桌面文件整理助手")
    app.setStyle("Fusion")
    ThemeManager.instance().apply(app)

    window = AppShell()
    window.show()
    # AR-2: non-blocking background update check (Option B). Deferred inside the
    # shell so the Dashboard is interactive first; never blocks startup.
    window.start_background_update_check()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
