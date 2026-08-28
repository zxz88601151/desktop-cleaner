"""Sidebar widget for the Premium App Shell (UI Migration Audit).

240px navigation rail: brand logo, menu (首页 / 智能整理 / 整理方案 /
整理历史 / 设置) and a safety reassurance card. Emits ``navigate(page_id)``
so the ``AppShell`` can route without the sidebar knowing page internals.
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

# P1-5: "整理方案" (CustomPage) is removed from the nav to keep the default
# UI minimal. The page object itself stays registered in AppShell._pages
# (an immutable test asserts its existence), it is simply no longer reachable
# from the sidebar.
_NAV = [
    ("home", "🏠", "首页"),
    ("organize", "✨", "智能整理"),
    ("history", "🕒", "整理历史"),
    ("tools", "🧰", "更多工具"),
    ("settings", "⚙", "设置"),
]


class Sidebar(QWidget):
    navigate = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(240)
        self._buttons: dict[str, QPushButton] = {}
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 22, 16, 22)
        root.setSpacing(6)

        # Brand
        brand = QHBoxLayout()
        brand.setSpacing(11)
        mark = QFrame()
        mark.setFixedSize(40, 40)
        mark.setObjectName("brand-mark")
        logo = QLabel()
        logo.setPixmap(_logo_pixmap())
        logo.setFixedSize(22, 22)
        mark.setLayout(QHBoxLayout())
        mark.layout().setContentsMargins(9, 9, 9, 9)
        mark.layout().addWidget(logo)
        name = QVBoxLayout()
        name.setSpacing(0)
        t = QLabel("Desktop Cleaner")
        t.setObjectName("sidebar-logo")
        s = QLabel("数字空间整理助手")
        s.setObjectName("sidebar-logo-sub")
        name.addWidget(t)
        name.addWidget(s)
        brand.addWidget(mark)
        brand.addLayout(name)
        root.addLayout(brand)

        # Nav
        nav_label = QLabel("菜单")
        nav_label.setObjectName("safety-li")
        nav_label.setStyleSheet("padding:14px 10px 6px;font-weight:600;")
        root.addWidget(nav_label)
        for pid, icon, label in _NAV:
            btn = QPushButton()
            btn.setObjectName("nav-item")
            btn.setProperty("active", "false")
            row = QHBoxLayout(btn)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(12)
            ic = QLabel(icon)
            ic.setFixedWidth(22)
            ic.setStyleSheet("font-size:17px;text-align:center;")
            tx = QLabel(label)
            row.addWidget(ic)
            row.addWidget(tx)
            btn.clicked.connect(lambda _=False, p=pid: self._select(p))
            self._buttons[pid] = btn
            root.addWidget(btn)

        root.addStretch(1)

        # Safety card
        safety = QFrame()
        safety.setObjectName("safety")
        sv = QVBoxLayout(safety)
        sv.setContentsMargins(16, 16, 16, 16)
        sv.setSpacing(10)
        head = QLabel("🛡 安全整理")
        head.setObjectName("safety-title")
        sv.addWidget(head)
        for item in ("不删除文件", "本地运行", "支持撤销"):
            li = QLabel(f"✓ {item}")
            li.setObjectName("safety-li")
            sv.addWidget(li)
        root.addWidget(safety)

    def _select(self, pid: str):
        self.set_active(pid)
        self.navigate.emit(pid)

    def set_active(self, pid: str):
        for k, btn in self._buttons.items():
            btn.setProperty("active", "true" if k == pid else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)


def _logo_pixmap():
    from PySide6.QtGui import QPixmap, QPainter, QColor, QPen
    from PySide6.QtCore import Qt, QRectF

    pm = QPixmap(22, 22)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#FFFFFF"), 1.8))
    p.setBrush(QColor(255, 255, 255, 40))
    p.drawRoundedRect(QRectF(2, 5, 14, 11), 2, 2)
    p.drawLine(8, 5, 8, 3)
    p.drawLine(13, 5, 13, 3)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(2, 5, 14, 11), 2, 2)
    p.end()
    return pm
