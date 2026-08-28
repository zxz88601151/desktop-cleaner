"""Custom plan page (整理方案) — choose a strategy, then start.

Persists the chosen mode + recursive flag into the settings KV store and
routes into the organize flow (OrganizePage reads those same settings on
entry, so this page is a real pre-configurator, not a fake selector).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

from data import settings_repo
from ui.theme_manager import ThemeManager
from ui.widgets.controls import ToggleSwitch
from PySide6.QtCore import Qt

_PLANS = [
    ("type", "🗂️", "按类型整理", "图片 / 文档 / 视频 / 音频 … 自动归类到对应文件夹"),
    ("date", "📅", "按日期整理", "按修改月份归入 2026-08 / 2026-09 等文件夹"),
]


class PlanCard(QFrame):
    clicked = Signal(str)

    def __init__(self, value, emoji, name, desc, parent=None):
        super().__init__(parent)
        self._value = value
        self.setObjectName("plan-card")
        self.setProperty("active", "false")
        lay = QHBoxLayout(self)
        lay.setSpacing(14)
        em = QLabel(emoji)
        em.setObjectName("plan-emoji")
        em.setFixedWidth(40)
        col = QVBoxLayout()
        col.setSpacing(4)
        nm = QLabel(name)
        nm.setObjectName("plan-name")
        ds = QLabel(desc)
        ds.setObjectName("plan-desc")
        ds.setWordWrap(True)
        col.addWidget(nm)
        col.addWidget(ds)
        badge = QLabel("✓ 已选")
        badge.setObjectName("badge")
        badge.setVisible(False)
        lay.addWidget(em)
        lay.addLayout(col, 1)
        lay.addWidget(badge)
        self._badge = badge

    def mousePressEvent(self, _):
        self.clicked.emit(self._value)

    def set_selected(self, on: bool):
        self.setProperty("active", "true" if on else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self._badge.setVisible(on)


class CustomPage(QWidget):
    navigate = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._mode = settings_repo.get("mode", "type") or "type"
        self._build()
        ThemeManager.instance().on_changed(self._on_theme)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title = QLabel("整理方案")
        title.setObjectName("page-title")
        sub = QLabel("选择一种整理策略，让数字空间焕然一新。")
        sub.setObjectName("page-sub")
        root.addWidget(title)
        root.addWidget(sub)

        body = QVBoxLayout()
        body.setSpacing(14)

        self._cards: dict[str, PlanCard] = {}
        for value, emoji, name, desc in _PLANS:
            card = PlanCard(value, emoji, name, desc)
            card.clicked.connect(self._select)
            self._cards[value] = card
            body.addWidget(card)

        # recursive toggle row
        rec_row = QHBoxLayout()
        rec_row.setSpacing(12)
        self._rec_toggle = ToggleSwitch(False)
        self._rec_toggle.toggled.connect(self._on_recursive)
        rec_label = QLabel("包含子文件夹")
        rec_label.setObjectName("set-label")
        rec_desc = QLabel("同时整理子目录中的文件")
        rec_desc.setObjectName("set-desc")
        rec_text = QVBoxLayout()
        rec_text.setSpacing(2)
        rec_text.addWidget(rec_label)
        rec_text.addWidget(rec_desc)
        rec_row.addLayout(rec_text, 1)
        rec_row.addWidget(self._rec_toggle)
        body.addLayout(rec_row)

        # source folder
        src_label = QLabel("整理文件夹")
        src_label.setObjectName("set-label")
        body.addWidget(src_label)
        src_row = QHBoxLayout()
        src_row.setSpacing(10)
        self._source = QLineEdit()
        self._source.setPlaceholderText("点击右侧按钮选择要整理的文件夹")
        browse = QPushButton("选择文件夹")
        browse.setObjectName("primary")
        browse.clicked.connect(self._browse)
        src_row.addWidget(self._source, 1)
        src_row.addWidget(browse)
        body.addLayout(src_row)

        root.addLayout(body, 1)

        # actions
        act = QHBoxLayout()
        act.setSpacing(12)
        start = QPushButton("开始整理")
        start.setObjectName("primary")
        start.setMinimumHeight(46)
        start.clicked.connect(self._start)
        back = QPushButton("返回首页")
        back.setObjectName("ghost")
        back.clicked.connect(lambda: self.navigate.emit("home"))
        act.addWidget(start)
        act.addWidget(back)
        act.addStretch(1)
        root.addLayout(act)

        self._sync_controls()

    def _select(self, value: str):
        self._mode = value
        for v, card in self._cards.items():
            card.set_selected(v == value)

    def _on_recursive(self, on: bool):
        settings_repo.set("recursive", int(on))

    def _browse(self):
        start = self._source.text() or str(Path.home())
        d = QFileDialog.getExistingDirectory(self, "选择要整理的文件夹", start)
        if d:
            self._source.setText(d)
            settings_repo.set("last_source", d)

    def _sync_controls(self):
        self._select(self._mode)
        self._rec_toggle.set_on(bool(int(settings_repo.get("recursive", 0) or 0)), silent=True)
        last = settings_repo.get("last_source")
        if last:
            self._source.setText(last)

    def _start(self):
        settings_repo.set("mode", self._mode)
        settings_repo.set("recursive", int(self._rec_toggle.is_on()))
        root = self._source.text().strip()
        if root:
            settings_repo.set("last_source", root)
        self.navigate.emit("organize")

    def _on_theme(self):
        self._rec_toggle.update()

    def on_enter(self):
        self._sync_controls()
