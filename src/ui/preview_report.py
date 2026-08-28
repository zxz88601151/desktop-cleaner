"""Pre-organize simulation report dialog (Feature 1, V1.1)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core import category_emoji
from utils import human_size

MAX_SAMPLES = 500


class PreviewReportDialog(QDialog):
    """Shows exactly what an organize run will do, before any file moves.

    The user must explicitly click *开始整理* to proceed, replacing the old
    plain yes/no confirmation with a trustworthy, detailed preview.
    """

    def __init__(self, report: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("整理模拟报告")
        self.setMinimumSize(680, 580)
        self.setModal(True)
        self._build(report)

    def _build(self, report: dict):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        # Root + organize mode (整理方式)
        root_label = QLabel(f"目标文件夹：{report['root']}")
        root_label.setObjectName("report-root")
        root_label.setWordWrap(True)
        layout.addWidget(root_label)

        mode = report.get("mode", "type")
        mode_text = "按类型整理" if mode == "type" else "按日期整理"
        mode_label = QLabel(f"整理方式：{mode_text}")
        mode_label.setObjectName("report-mode")
        layout.addWidget(mode_label)

        summary = QLabel(
            f"本次将整理 <b>{report['total']}</b> 个文件"
            f"（共 {human_size(report['total_size'])}），"
            "文件仅移动、不删除，可随时撤销。"
        )
        summary.setObjectName("report-summary")
        layout.addWidget(summary)

        op_note = QLabel(f"预计操作：移动 <b>{report['total']}</b> 个文件到对应分类文件夹")
        op_note.setObjectName("report-note")
        layout.addWidget(op_note)
        layout.addWidget(self._separator())

        # Category breakdown table
        cats = report["categories"]
        table = QTableWidget(len(cats), 4)
        table.setHorizontalHeaderLabels(["分类", "目标文件夹", "文件数", "大小"])
        table.horizontalHeader().setStretchLastSection(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        from PySide6.QtWidgets import QHeaderView

        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for r, c in enumerate(cats):
            emoji = c.get("emoji", category_emoji(c["label"]))
            table.setItem(r, 0, QTableWidgetItem(f"{emoji} {c['label']}"))
            table.setItem(r, 1, QTableWidgetItem(c["target"]))
            table.setItem(r, 2, QTableWidgetItem(str(c["count"])))
            table.setItem(r, 3, QTableWidgetItem(human_size(c["size"])))
        table.resizeRowsToContents()
        layout.addWidget(table, 1)

        layout.addWidget(self._separator())

        # Move detail preview
        detail_label = QLabel("移动明细预览：")
        detail_label.setObjectName("report-detail")
        layout.addWidget(detail_label)

        flat: list[tuple[str, str]] = []
        for c in cats:
            flat.extend(c["samples"])
        if len(flat) > MAX_SAMPLES:
            flat = flat[:MAX_SAMPLES]

        detail = QListWidget()
        detail.setAlternatingRowColors(True)
        shown = 0
        for name, rel in flat:
            item = QListWidgetItem(f"{name}   →   {rel}")
            detail.addItem(item)
            shown += 1
        layout.addWidget(detail, 2)

        note = QLabel(
            f"仅显示前 {shown} 条；完整列表将在整理时逐条执行。"
            if shown < report["total"]
            else f"共 {report['total']} 条移动。"
        )
        note.setObjectName("report-note")
        layout.addWidget(note)

        warn = QLabel("注意：文件不会删除，可随时撤销。")
        warn.setObjectName("report-warn")
        layout.addWidget(warn)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("ghost")
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("开始整理")
        ok_btn.setObjectName("primary")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    @staticmethod
    def _separator() -> QFrame:
        f = QFrame()
        f.setObjectName("separator")
        f.setFrameShape(QFrame.HLine)
        return f
