"""Home dashboard with summary stat cards (Feature 2, V1.1; restyled V1.2)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from data import history_repo
from ui.icons import color, pixmap


class StatCard(QFrame):
    """A single flat summary card (no shadow — hierarchy via surface + border)."""

    def __init__(self, icon_name: str, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(96)

        icon = QLabel()
        icon.setObjectName("stat-icon")
        icon.setFixedSize(24, 24)
        icon.setPixmap(pixmap(icon_name, color("text_secondary"), 24))
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

    def set_value(self, text: str) -> None:
        self._value.setText(text)


class DashboardWidget(QWidget):
    """Three-card summary: cumulative files / runs / last run time."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._cards = {
            "total": StatCard("document", "累计整理文件"),
            "runs": StatCard("refresh", "整理次数"),
            "last": StatCard("clock", "最近整理"),
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
