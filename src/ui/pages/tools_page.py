"""Tools page (更多工具) — Coming Soon showcase for the 中哥工具箱 roadmap.

Reads exclusively from ``ui.features`` (the single source of truth). Every
card is fully visible and clickable; clicking opens the unified
:class:`~ui.coming_soon.ComingSoonDialog`. No future feature performs any
action here — this page is a product preview, not a feature launcher.

No business logic, no DB, no core/data access.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QGridLayout,
    QHBoxLayout,
    QScrollArea,
    QWidget,
    QVBoxLayout,
)

from ui.features import FeatureStatus, get_features
from ui.coming_soon import ComingSoonDialog


class ToolCard(QFrame):
    """A single future-tool teaser card. Click opens its Coming Soon dialog."""

    clicked = Signal(object)  # FeatureDefinition

    def __init__(self, feature, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("tool-card")
        self._feature = feature

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        top = QHBoxLayout()
        ic = QLabel(feature.icon)
        ic.setObjectName("tool-icon")
        name = QLabel(feature.name)
        name.setObjectName("tool-name")
        badge = QLabel(feature.status_label)
        badge.setObjectName("tool-badge")
        badge.setProperty(
            "state",
            "coming" if feature.status == FeatureStatus.COMING_SOON else "planned",
        )
        badge.style().unpolish(badge)
        badge.style().polish(badge)
        top.addWidget(ic)
        top.addStretch(1)
        top.addWidget(badge)
        lay.addLayout(top)

        desc = QLabel(feature.description)
        desc.setObjectName("tool-desc")
        desc.setWordWrap(True)
        lay.addWidget(name)
        lay.addWidget(desc)
        lay.addStretch(1)

        cta = QLabel("了解功能 →")
        cta.setObjectName("ghost-link")
        lay.addWidget(cta, alignment=Qt.AlignmentFlag.AlignLeft)

    def mousePressEvent(self, _):
        self.clicked.emit(self._feature)


class ToolsPage(QWidget):
    """Landing surface that lists every non-AVAILABLE feature from the registry."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title = QLabel("更多工具")
        title.setObjectName("page-title")
        sub = QLabel("正在持续增加更多实用功能")
        sub.setObjectName("page-sub")
        root.addWidget(title)
        root.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        grid = QWidget()
        self._grid = QGridLayout(grid)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(16)
        scroll.setWidget(grid)
        root.addWidget(scroll, 1)

        self._populate()

    def _populate(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        features = get_features()
        cols = 2
        for i, f in enumerate(features):
            card = ToolCard(f)
            card.clicked.connect(self._open)
            self._grid.addWidget(card, i // cols, i % cols)

    def _open(self, feature):
        ComingSoonDialog(feature, self).exec()

    def on_enter(self):
        # Registry is static; nothing to refresh. Kept for the page contract.
        pass
