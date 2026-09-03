"""Update notification dialog (Option B — check-only).

Minimal, on-brand modal that appears only when a newer version exists. Shows the
new version + release notes and offers:
- [立即查看] -> open the official download / release page in the browser
- [稍后]     -> dismiss (hidden when the update is FORCEd)

It does NOT download or replace anything. Visual style reuses the existing dialog
tokens (`dialog-title` / `dialog-body` / `primary` / `ghost`) so it stays consistent
with the rest of the app without altering the established visual system.
"""
from __future__ import annotations

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from .constants import is_allowed_download_url
from .version import is_older_than


class UpdateDialog(QDialog):
    def __init__(self, manifest: dict, current_version: str, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setObjectName("update-dialog")
        self.setMinimumWidth(440)
        self.setWindowTitle("发现新版本")
        # Phase E.3: never open a manifest-supplied URL that did not pass the
        # HTTPS + host allowlist check (no arbitrary / internal / http URL).
        self._url = manifest.get("download_url") or ""
        self._valid = is_allowed_download_url(self._url)
        self._forced = bool(
            manifest.get("minimum_supported_version")
            and is_older_than(manifest["minimum_supported_version"], current_version)
        )
        self._build(manifest, current_version)

    def _build(self, manifest, current_version):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(12)

        title = QLabel("发现新版本")
        title.setObjectName("dialog-title")
        latest = QLabel(f"Desktop Cleaner {manifest.get('latest_version', '')}")
        latest.setObjectName("about-version")
        root.addWidget(title)
        root.addWidget(latest)

        notes = manifest.get("release_notes") or []
        if notes:
            body = QLabel("• " + "\n• ".join(notes))
            body.setObjectName("dialog-body")
            body.setWordWrap(True)
            root.addWidget(body)

        if self._forced:
            warn = QLabel("当前版本已停止支持，请尽快更新以继续使用。")
            warn.setObjectName("dialog-body")
            warn.setWordWrap(True)
            root.addWidget(warn)

        row = QHBoxLayout()
        row.addStretch(1)
        if not self._forced:
            later = QPushButton("稍后")
            later.setObjectName("ghost")
            later.clicked.connect(self.reject)
            row.addWidget(later)
        if self._valid:
            view = QPushButton("立即查看")
            view.setObjectName("primary")
            view.setDefault(True)
            view.clicked.connect(self._open)
            row.addWidget(view)
        else:
            # No safe download URL: do not offer an open button (E.3 §9).
            unsafe = QLabel("下载链接不可用，请稍后再试。")
            unsafe.setObjectName("dialog-body")
            unsafe.setWordWrap(True)
            root.addWidget(unsafe)
        root.addLayout(row)

    def _open(self):
        QDesktopServices.openUrl(QUrl(self._url))
        self.accept()
