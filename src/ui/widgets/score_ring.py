"""Circular progress ring widget (Clean Score + execute progress).

Drawn with :class:`QPainter` so it themes correctly and needs no SVG.
Used both for the Dashboard "电脑整洁度" ring and the organize
"整理中" progress ring.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ui.theme.themes import THEMES
from ui.theme_manager import ThemeManager


class ScoreRing(QWidget):
    def __init__(self, value: int = 0, size: int = 240, thickness: int = 16, parent=None):
        super().__init__(parent)
        self._value = max(0, min(100, value))
        self._size = size
        self._thickness = thickness
        self.setFixedSize(size, size)

    def setValue(self, value: int):
        self._value = max(0, min(100, value))
        self.update()

    def paintEvent(self, _):
        palette = THEMES.get(ThemeManager.instance().theme, THEMES["light"])
        accent = QColor(palette["accent"])
        track = QColor(palette["border"])
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self._size // 2
        rad = r - self._thickness // 2 - 1
        # track
        p.setPen(QPen(track, self._thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawEllipse(self._thickness // 2, self._thickness // 2, rad * 2, rad * 2)
        # value arc (start at top, sweep clockwise)
        span = int(360 * 16 * self._value / 100)
        p.setPen(QPen(accent, self._thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(self._thickness // 2, self._thickness // 2, rad * 2, rad * 2, 90 * 16, -span)
        p.end()
