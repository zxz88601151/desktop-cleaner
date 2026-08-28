"""Settings page (设置) — real, persisted preferences.

Wires the UI controls to the settings KV store and the live theme manager:
- 深色模式   -> ThemeManager (applies immediately, persisted)
- 整理方式   -> settings_repo "mode"  (used by organize / custom pages)
- 子文件夹   -> settings_repo "recursive"
- 关于       -> AboutDialog
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from data import settings_repo
from ui.about import AboutDialog
from ui.theme_manager import ThemeManager
from ui.widgets.controls import Segmented, ToggleSwitch


class SettingsPage(QWidget):
    # AR-2: user-initiated "check for updates" (bypasses the 24h throttle).
    check_update = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build()
        ThemeManager.instance().on_changed(self._on_theme)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(8)

        title = QLabel("设置")
        title.setObjectName("page-title")
        sub = QLabel("偏好会立即生效并自动保存。")
        sub.setObjectName("page-sub")
        root.addWidget(title)
        root.addWidget(sub)

        body = QVBoxLayout()
        body.setSpacing(0)
        body.addLayout(self._theme_row())
        body.addLayout(self._mode_row())
        body.addLayout(self._recursive_row())
        body.addLayout(self._update_row())
        body.addLayout(self._about_row())
        root.addLayout(body, 1)
        root.addStretch(1)

    # ---- rows -------------------------------------------------------------- #
    def _row(self, label: str, desc: str, control) -> QVBoxLayout:
        wrapper = QFrame()
        wrapper.setObjectName("set-row")
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        text = QVBoxLayout()
        text.setSpacing(2)
        l = QLabel(label)
        l.setObjectName("set-label")
        d = QLabel(desc)
        d.setObjectName("set-desc")
        text.addWidget(l)
        text.addWidget(d)
        row.addLayout(text, 1)
        row.addWidget(control)
        lay = QVBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(wrapper)
        return lay

    def _theme_row(self):
        self._theme_toggle = ToggleSwitch(ThemeManager.instance().is_dark)
        self._theme_toggle.toggled.connect(self._on_theme_toggle)
        return self._row(
            "深色模式",
            "切换浅色 / 深色界面主题",
            self._theme_toggle,
        )

    def _mode_row(self):
        self._mode_seg = Segmented([("type", "按类型"), ("date", "按日期")])
        cur = settings_repo.get("mode", "type") or "type"
        self._mode_seg.set_value(cur)
        self._mode_seg.selected.connect(
            lambda v: settings_repo.set("mode", v)
        )
        return self._row(
            "默认整理方式",
            "新建整理时使用的默认方式",
            self._mode_seg,
        )

    def _recursive_row(self):
        self._rec_toggle = ToggleSwitch(bool(int(settings_repo.get("recursive", 0) or 0)))
        self._rec_toggle.toggled.connect(
            lambda on: settings_repo.set("recursive", int(on))
        )
        return self._row(
            "包含子文件夹",
            "整理时一并处理子目录中的文件",
            self._rec_toggle,
        )

    def _update_row(self):
        btn = QPushButton("检查更新")
        btn.setObjectName("ghost")
        btn.clicked.connect(self.check_update.emit)
        return self._row(
            "检查更新",
            "检查是否有新版本（后台进行，不影响使用）",
            btn,
        )

    def _about_row(self):
        btn = QPushButton("关于本软件")
        btn.setObjectName("primary")
        btn.clicked.connect(lambda: AboutDialog(self).exec())
        return self._row(
            "关于",
            "版本、功能与开发者信息",
            btn,
        )

    # ---- handlers ---------------------------------------------------------- #
    def _on_theme_toggle(self, on: bool):
        ThemeManager.instance().set_theme("dark" if on else "light")

    def _on_theme(self):
        # reflect external theme changes (e.g. top-bar toggle)
        self._theme_toggle.set_on(ThemeManager.instance().is_dark, silent=True)
        self._rec_toggle.update()

    def on_enter(self):
        pass
