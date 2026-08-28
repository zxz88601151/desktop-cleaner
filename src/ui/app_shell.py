"""App Shell — the Premium multi-page frame (UI Migration Audit, full impl).

A 240px :class:`Sidebar` + a top bar (title + theme toggle + about) + a
:class:`QStackedWidget` page router. The shell knows nothing about page
internals: it only routes ``navigate`` signals and calls ``on_enter()`` on
the active page so each page can refresh itself from the business layer.
"""
from __future__ import annotations

from PySide6.QtCore import QSize, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from data import database
from data import settings_repo
from update.manager import UpdateManager
from update.update_dialog import UpdateDialog
from ui.about import AboutDialog
from ui.icons import color, icon
from ui.pages.custom_page import CustomPage
from ui.pages.dashboard_page import DashboardPage
from ui.pages.history_page import HistoryPage
from ui.pages.organize_page import OrganizePage
from ui.pages.settings_page import SettingsPage
from ui.theme_manager import ThemeManager
from ui.welcome import WelcomeDialog, should_show_welcome
from ui.widgets.sidebar import Sidebar
from version import __version__

_TITLES = {
    "home": "首页",
    "organize": "整理",
    "custom": "整理方案",
    "history": "整理历史",
    "settings": "设置",
}


class AppShell(QWidget):
    def __init__(self):
        super().__init__()
        database.init_db()
        self.setWindowTitle("桌面文件整理助手 · Desktop Cleaner")
        self.resize(1080, 760)
        self.setMinimumSize(900, 620)  # P1-6: responsive floor
        self._pages: dict[str, QWidget] = {}
        self._build()
        ThemeManager.instance().on_changed(self._on_theme)
        # UI-1.3 Phase 1.5: default landing route is 整理 (Product Home).
        self._route("organize")
        if should_show_welcome():
            WelcomeDialog(self).exec()

        # AR-2: in-app update system (Option B — check-only, non-blocking).
        # No auto-start here: main.py triggers the background check after show so
        # unit tests that build AppShell directly never hit the network.
        self._manual_check_pending = False
        self._update_mgr = UpdateManager(__version__, self)
        self._update_mgr.update_available.connect(self._on_update_available)
        self._update_mgr.no_update.connect(self._on_no_update)
        self._pages["settings"].check_update.connect(self._on_manual_check_requested)

    # ----------------------------- build --------------------------------- #
    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.navigate.connect(self._route)
        root.addWidget(self.sidebar)

        # right column
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)
        right.addWidget(self._build_topbar())

        self.stack = QStackedWidget()
        self._pages = {
            "home": DashboardPage(),
            "organize": OrganizePage(),
            "custom": CustomPage(),
            "history": HistoryPage(),
            "settings": SettingsPage(),
        }
        for page in self._pages.values():
            self.stack.addWidget(page)
            # route navigate signals from any page back through the shell
            if hasattr(page, "navigate"):
                page.navigate.connect(self._route)  # type: ignore[attr-defined]
        # refresh the dashboard whenever a run finishes somewhere
        self._pages["organize"].finished.connect(self._pages["home"].refresh)  # type: ignore[attr-defined]
        self._pages["history"].finished.connect(self._pages["home"].refresh)  # type: ignore[attr-defined]
        # P0: dashboard hero "开始扫描" launches the organize flow directly
        self._pages["home"].start_scan.connect(self._start_organize_from_dashboard)  # type: ignore[attr-defined]
        right.addWidget(self.stack, 1)

        root.addLayout(right, 1)

    def _build_topbar(self):
        bar = QWidget()
        bar.setObjectName("topbar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(28, 16, 28, 16)
        lay.setSpacing(12)
        self._title = QLabel("整理")
        self._title.setObjectName("page-title")
        lay.addWidget(self._title)
        lay.addStretch(1)

        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("icon")
        self.theme_btn.setFixedSize(38, 34)
        self.theme_btn.setToolTip("切换主题（浅色 / 深色）")
        self.theme_btn.clicked.connect(lambda: ThemeManager.instance().toggle())
        self.about_btn = QPushButton("关于")
        self.about_btn.setObjectName("ghost")
        self.about_btn.clicked.connect(lambda: AboutDialog(self).exec())
        lay.addWidget(self.about_btn)
        lay.addWidget(self.theme_btn)
        self._update_theme_btn()
        return bar

    # ----------------------------- routing -------------------------------- #
    def _route(self, pid: str):
        # "about" is a modal dialog, not a stacked page.
        if pid == "about":
            AboutDialog(self).exec()
            return
        page = self._pages.get(pid)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        self.sidebar.set_active(pid)
        self._title.setText(_TITLES.get(pid, pid))
        enter = getattr(page, "on_enter", None)
        if callable(enter):
            enter()

    def _start_organize_from_dashboard(self, root: str):
        """P0: dashboard hero launched a scan — pre-fill the organize source,
        route to that page, and kick off the real scan. No business-logic
        change; this only orchestrates existing page methods."""
        org = self._pages["organize"]
        org.set_source(root)  # type: ignore[attr-defined]
        self._route("organize")
        org._start_scan()  # type: ignore[attr-defined]

    # ----------------------------- theme ---------------------------------- #
    def _update_theme_btn(self):
        dark = ThemeManager.instance().is_dark
        self.theme_btn.setIcon(icon("moon" if dark else "sun", color("text_secondary"), 18))
        self.theme_btn.setIconSize(QSize(18, 18))

    def _on_theme(self):
        self._update_theme_btn()

    # ----------------------------- update --------------------------------- #
    def start_background_update_check(self):
        """Deferred, non-blocking update check. Called by main.py after show().

        Uses a short timer so the Dashboard is on screen first; the actual network
        fetch runs on a worker thread and never blocks startup.
        """
        QTimer.singleShot(2000, lambda: self._update_mgr.start_check())

    def _on_manual_check_requested(self):
        """Settings page "检查更新" button. Bypasses the 24h throttle."""
        self._manual_check_pending = True
        self._update_mgr.start_check(force=True)

    def _on_update_available(self, manifest):
        UpdateDialog(manifest, __version__, self).exec()
        self._manual_check_pending = False

    def _on_no_update(self):
        # Background checks stay silent. A manual check reports "up to date".
        if self._manual_check_pending:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(self, "检查更新", "当前已是最新版本。")
        self._manual_check_pending = False
