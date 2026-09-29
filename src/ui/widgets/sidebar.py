"""Sidebar widget for the Premium App Shell (UI-1.3 Phase 1 + Phase 1.5).

240px navigation rail: brand logo, primary menu (整理 / 整理历史 / 设置),
a thin divider, and a bottom "关于" entry. Emits ``navigate(page_id)``
so the ``AppShell`` can route without the sidebar knowing page internals.

UI-1.3 Phase 1.5: the standalone "首页" entry is removed — the 整理 page now
acts as the Product Home and is the default landing route. Navigation is closed
to exactly four entries: 整理 / 历史 / 设置 / 关于.

All icons are drawn from :mod:`ui.icons` (line icons) — no emoji.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.icons import color, pixmap
from ui.theme_manager import ThemeManager

# P1-5: "整理方案" (CustomPage) is removed from the nav to keep the default
# UI minimal. The page object itself stays registered in AppShell._pages
# (an immutable test asserts its existence), it is simply no longer reachable
# from the sidebar.
# UI-1.3: "更多工具" / Tools removed from product UI (Decision 02).
# UI-1.3 Phase 1.5: "首页" removed from the nav — 整理 is the Product Home and
# the default route. Navigation is closed to 整理 / 历史 / 设置 (+ bottom 关于).
_NAV = [
    ("organize", "sort", "整理"),
    ("analysis", "chart", "文件夹分析"),
    ("empty", "open_folder", "空文件夹"),
    ("history", "history", "整理历史"),
    ("settings", "settings", "设置"),
    ("rules", "sliders", "自定义规则"),
]

_BOTTOM = [
    ("about", "info", "关于"),
]


class Sidebar(QWidget):
    navigate = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(240)
        self._buttons: dict[str, QPushButton] = {}
        self._nav_icons: dict[str, tuple[QLabel, str]] = {}
        self._build()
        ThemeManager.instance().on_changed(self._refresh_icons)

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
        self._add_nav_group(_NAV, root)

        root.addStretch(1)

        # Divider + bottom (关于)
        div = QFrame()
        div.setObjectName("nav-divider")
        root.addWidget(div)
        self._add_nav_group(_BOTTOM, root)

        # Safety card
        safety = QFrame()
        safety.setObjectName("safety")
        sv = QVBoxLayout(safety)
        sv.setContentsMargins(16, 16, 16, 16)
        sv.setSpacing(10)
        head = QLabel("安全整理")
        head.setObjectName("safety-title")
        sv.addWidget(head)
        for item in ("不删除文件", "本地运行", "支持撤销"):
            li = QLabel(f"✓ {item}")
            li.setObjectName("safety-li")
            sv.addWidget(li)
        root.addWidget(safety)

        self._refresh_icons()

    def _add_nav_group(self, items, root: QVBoxLayout):
        for pid, icon_name, label in items:
            btn = QPushButton()
            btn.setObjectName("nav-item")
            btn.setProperty("active", "false")
            row = QHBoxLayout(btn)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(12)
            ic = QLabel()
            ic.setObjectName("nav-icon")
            ic.setFixedSize(20, 20)
            tx = QLabel(label)
            row.addWidget(ic)
            row.addWidget(tx)
            btn.clicked.connect(lambda _=False, p=pid: self._select(p))
            self._buttons[pid] = btn
            self._nav_icons[pid] = (ic, icon_name)
            root.addWidget(btn)

    def _select(self, pid: str):
        self.set_active(pid)
        self.navigate.emit(pid)

    def set_active(self, pid: str):
        for k, btn in self._buttons.items():
            btn.setProperty("active", "true" if k == pid else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._refresh_icons()

    def _refresh_icons(self) -> None:
        """Re-colour every nav icon from the active theme.

        Active items use the accent; inactive items use the muted text colour.
        """
        active_col = color("accent")
        idle_col = color("text_secondary")
        for pid, (ic, name) in self._nav_icons.items():
            col = active_col if self._buttons[pid].property("active") == "true" else idle_col
            ic.setPixmap(pixmap(name, col, 20))


def _logo_pixmap():
    """Brand glyph (a small folder) painted in ``on_accent`` on the accent mark."""
    stroke = QColor(color("on_accent"))
    fill = QColor(color("on_accent"))
    fill.setAlpha(40)

    pm = QPixmap(22, 22)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(stroke, 1.8))
    p.setBrush(fill)
    p.drawRoundedRect(QRectF(2, 5, 14, 11), 2, 2)
    p.drawLine(8, 5, 8, 3)
    p.drawLine(13, 5, 13, 3)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(2, 5, 14, 11), 2, 2)
    p.end()
    return pm
