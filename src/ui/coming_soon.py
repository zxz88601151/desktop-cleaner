"""Coming Soon dialog — unified, non-functional teaser for future tools.

Shows a future feature's icon / name / description / status and a single
Ghost "返回" button. It performs NO business action; clicking the button
(or pressing Enter / Esc, or the window close button) simply dismisses the
dialog. No feature logic, no DB, no core/data access.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
)

from ui.features import FeatureDefinition, FeatureStatus


class ComingSoonDialog(QDialog):
    """Teaser dialog for a not-yet-shipped feature (read-only, safe to close)."""

    def __init__(self, feature: FeatureDefinition, parent=None):
        super().__init__(parent)
        self.setWindowTitle(feature.name)
        self.setMinimumWidth(420)
        self.setModal(True)
        self.setObjectName("coming-soon")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 20)
        lay.setSpacing(14)

        icon = QLabel(feature.icon)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size:40px;")
        lay.addWidget(icon)

        title = QLabel(feature.name)
        title.setObjectName("dialog-title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        badge = QLabel(feature.status_label)
        badge.setObjectName("tool-badge")
        badge.setProperty(
            "state",
            "coming" if feature.status == FeatureStatus.COMING_SOON else "planned",
        )
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.style().unpolish(badge)
        badge.style().polish(badge)
        lay.addWidget(badge)

        body = QLabel(
            f"{feature.description}\n\n"
            "这个功能正在开发中，我们会在后续版本中加入。"
        )
        body.setObjectName("dialog-body")
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(body)

        btn = QPushButton("返回")
        btn.setObjectName("ghost")
        btn.setMinimumWidth(120)
        btn.setDefault(True)
        btn.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(btn)
        lay.addLayout(row)
