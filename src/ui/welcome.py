"""First-launch welcome dialog (Feature 3, V1.1).

Shows once on first run, explaining the product's safety guarantees
(local-only, no deletion, undoable). The dismissal is recorded in the
settings KV store so the dialog never appears again.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from data import settings_repo

_BULLETS = [
    ("本地运行", "文件不会上传，一切都在你的电脑上完成。"),
    ("只移动不删除", "整理只是把文件分类归拢，绝不会删除你的文件。"),
    ("一键自动分类", "按类型或日期自动整理，桌面 / 下载瞬间清爽。"),
    ("整理前可预览", "执行前先看模拟报告，确认分类方案再动手。"),
    ("不会覆盖已有文件", "同名文件自动重命名，绝不覆盖你原来的文件。"),
    ("支持撤销", "每次整理都可一键还原，文件随时回到原处。"),
]


def should_show_welcome() -> bool:
    """Return True when the welcome dialog has never been dismissed."""
    return settings_repo.get("first_launch_completed") is None


class WelcomeDialog(QDialog):
    """One-time onboarding dialog shown on first launch."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("欢迎使用 Desktop Cleaner")
        self.setFixedSize(460, 380)
        self.setModal(True)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(14)

        title = QLabel("欢迎使用 Desktop Cleaner")
        title.setObjectName("welcome-title")
        sub = QLabel("你的本地文件整理助手 · 每天一个使用小工具")
        sub.setObjectName("welcome-sub")
        layout.addWidget(title)
        layout.addWidget(sub)
        layout.addWidget(self._separator())

        bullets = QVBoxLayout()
        bullets.setSpacing(12)
        for head, detail in _BULLETS:
            row = QHBoxLayout()
            row.setSpacing(10)
            check = QLabel("✓")
            check.setObjectName("welcome-check")
            text = QLabel(f"<b>{head}</b> — {detail}")
            text.setObjectName("welcome-bullet")
            text.setWordWrap(True)
            row.addWidget(check)
            row.addWidget(text, 1)
            bullets.addLayout(row)
        layout.addLayout(bullets, 1)

        note = QLabel("点击「开始使用」即表示你了解：文件仅移动、不删除、可撤销。")
        note.setObjectName("welcome-note")
        note.setWordWrap(True)
        layout.addWidget(note)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        start_btn = QPushButton("开始使用")
        start_btn.setObjectName("primary")
        start_btn.setMinimumWidth(120)
        start_btn.setDefault(True)
        start_btn.clicked.connect(self.accept)
        btn_row.addWidget(start_btn)
        layout.addLayout(btn_row)

    def accept(self):
        settings_repo.set("first_launch_completed", 1)
        super().accept()

    @staticmethod
    def _separator() -> QFrame:
        f = QFrame()
        f.setObjectName("separator")
        f.setFrameShape(QFrame.HLine)
        return f
