"""About dialog (Feature 4, V1.1)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ui.icons import color, pixmap
from version import APP_NAME, APP_NAME_ZH, AUTHOR, COPYRIGHT_TEXT, TAGLINE, __version__

_FEATURES = [
    ("folder", "一键整理桌面 / 下载等杂乱文件夹"),
    ("sort", "按类型或日期自动分类归拢"),
    ("eye", "整理前生成模拟报告，确认后才执行"),
    ("undo", "每次整理均可一键撤销还原"),
    ("lock", "完全本地运行，文件不上传"),
]


class AboutDialog(QDialog):
    """Product information dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setFixedSize(440, 420)
        self.setModal(True)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(12)

        name = QLabel(APP_NAME)
        name.setObjectName("about-name")
        version = QLabel(f"版本 {__version__}  ·  {APP_NAME_ZH}")
        version.setObjectName("about-version")
        tagline = QLabel(TAGLINE)
        tagline.setObjectName("about-tagline")
        layout.addWidget(name)
        layout.addWidget(version)
        layout.addWidget(tagline)
        layout.addWidget(self._separator())

        feat = QVBoxLayout()
        feat.setSpacing(10)
        for icon_name, text in _FEATURES:
            row = QHBoxLayout()
            row.setSpacing(10)
            ic = QLabel()
            ic.setFixedSize(20, 20)
            ic.setPixmap(pixmap(icon_name, color("text_secondary"), 20))
            tx = QLabel(text)
            tx.setObjectName("about-feature")
            tx.setWordWrap(True)
            row.addWidget(ic)
            row.addWidget(tx, 1)
            feat.addLayout(row)
        layout.addLayout(feat, 1)

        author = QLabel(COPYRIGHT_TEXT)
        author.setObjectName("about-author")
        layout.addWidget(author)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        ok_btn = QPushButton("关闭")
        ok_btn.setObjectName("primary")
        ok_btn.setMinimumWidth(100)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    @staticmethod
    def _separator() -> QFrame:
        f = QFrame()
        f.setObjectName("separator")
        f.setFrameShape(QFrame.HLine)
        return f
