"""Premium reusable controls (UI Migration Audit, Phase 1+).

- :class:`ToggleSwitch` : a pill toggle drawn with :class:`QPainter` so it
  themes correctly (no SVG, reads the active palette directly).
- :class:`Segmented`     : a segmented control backed by real ``QPushButton``
  children styled via the ``#seg`` / ``#seg QPushButton`` QSS rules.

Both are presentation-only and emit their value through Qt signals; the
calling page decides what (if any) business state to persist.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QPushButton, QWidget

from ui.theme.themes import THEMES
from ui.theme_manager import ThemeManager


def _palette() -> dict:
    return THEMES.get(ThemeManager.instance().theme, THEMES["light"])


class ToggleSwitch(QWidget):
    """A 46x26 pill toggle. On = accent fill, knob slides right."""

    toggled = Signal(bool)

    def __init__(self, on: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self._on = bool(on)
        self.setFixedSize(46, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # ---- state ----------------------------------------------------------- #
    def is_on(self) -> bool:
        return self._on

    def set_on(self, value: bool, silent: bool = False) -> None:
        value = bool(value)
        if value == self._on:
            return
        self._on = value
        self.update()
        if not silent:
            self.toggled.emit(self._on)

    # ---- interaction ----------------------------------------------------- #
    def mousePressEvent(self, _):
        self._on = not self._on
        self.update()
        self.toggled.emit(self._on)

    # ---- paint ----------------------------------------------------------- #
    def paintEvent(self, _):
        palette = _palette()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = self.height()
        r = h / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(palette["accent"] if self._on else palette["border_strong"]))
        p.drawRoundedRect(0, 0, self.width(), h, r, r)
        knob = QColor(palette["surface"])
        kx = self.width() - h - 3 if self._on else 3
        p.setBrush(knob)
        p.drawEllipse(kx, 3, h - 6, h - 6)
        p.end()


class Segmented(QWidget):
    """A segmented control. ``options`` is a list of ``(value, label)``."""

    selected = Signal(str)

    def __init__(self, options, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("seg")
        from PySide6.QtWidgets import QHBoxLayout

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)
        self._buttons: dict[str, QPushButton] = {}
        for value, label in options:
            btn = QPushButton(label)
            btn.setObjectName("seg-btn")
            btn.setProperty("on", "false")
            btn.clicked.connect(lambda _=False, v=value: self._choose(v))  # noqa: B023
            self._buttons[value] = btn
            lay.addWidget(btn, 1)

    def _choose(self, value: str) -> None:
        for v, btn in self._buttons.items():
            on = "true" if v == value else "false"
            if btn.property("on") != on:
                btn.setProperty("on", on)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
        self.selected.emit(value)

    def set_value(self, value: str) -> None:
        if value in self._buttons:
            self._choose(value)

    def value(self) -> str | None:
        for v, btn in self._buttons.items():
            if btn.property("on") == "true":
                return v
        return None
