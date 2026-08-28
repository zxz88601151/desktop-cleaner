"""Home dashboard with summary stat cards (Feature 2, V1.1; restyled V1.2)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from data import history_repo
from ui.theme_manager import ThemeManager


class StatCard(QFrame):
    """A single rounded, shadowed summary card."""

    def __init__(self, emoji: str, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(96)

        icon = QLabel(emoji)
        icon.setObjectName("stat-icon")
        self._value = QLabel("—")
        self._value.setObjectName("stat-value")
        self._label = QLabel(label)
        self._label.setObjectName("stat-label")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(4)
        lay.addWidget(icon)
        lay.addWidget(self._value)
        lay.addWidget(self._label)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._apply_shadow()

    def set_value(self, text: str) -> None:
        self._value.setText(text)

    def _apply_shadow(self) -> None:
        self._shadow.setBlurRadius(16)
        self._shadow.setOffset(0, 3)
        self._shadow.setColor(ThemeManager.instance().shadow_color())
        self.setGraphicsEffect(self._shadow)

    def refresh_shadow(self) -> None:
        self._shadow.setColor(ThemeManager.instance().shadow_color())


class DashboardWidget(QWidget):
    """Three-card summary: cumulative files / runs / last run time."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._cards = {
            "total": StatCard("📁", "累计整理文件"),
            "runs": StatCard("🔄", "整理次数"),
            "last": StatCard("🕒", "最近整理"),
        }
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)
        lay.addWidget(self._cards["total"], 1)
        lay.addWidget(self._cards["runs"], 1)
        lay.addWidget(self._cards["last"], 1)
        self.refresh()

    def refresh(self) -> None:
        stats = history_repo.get_stats()
        self._cards["total"].set_value(f"{stats['total_files']:,}")
        self._cards["runs"].set_value(f"{stats['runs']:,}")
        last = stats["last_time"]
        self._cards["last"].set_value(last[:10] if last else "—")

    def refresh_shadows(self) -> None:
        for card in self._cards.values():
            card.refresh_shadow()
