"""About dialog (Feature 4, V1.1).

Phase E.1: author info / photo / copyright / fingerprint.
Phase E.3: a lightweight "检查更新" entry that fetches the public HTTPS manifest
on a worker thread, compares versions (reusing `update.checker` / `update.decision`)
and reports one of UP_TO_DATE / UPDATE_AVAILABLE / ERROR. It never auto-downloads
or auto-installs; the download button only opens a URL that passed the HTTPS +
host allowlist check (`update.constants.is_allowed_download_url`).
"""
from __future__ import annotations

from PySide6.QtCore import QThread, QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ui.icons import color, pixmap
from update.checker import fetch_manifest
from update.constants import (
    UPDATE_MANIFEST_URL,
    is_allowed_download_url,
    validate_manifest_basics,
)
from update.decision import LEVEL_NONE, evaluate
from version import (
    APP_NAME,
    APP_NAME_ZH,
    AUTHOR_NAME,
    CONTACT_WECHAT,
    COPYRIGHT_TEXT,
    TAGLINE,
    __version__,
)

_PHOTO_SIZE = 100


def _resource_path(name: str) -> str:
    """Resolve a bundled data file for both source and PyInstaller runs."""
    import sys
    from pathlib import Path

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return str(Path(meipass) / name)
    return str(Path(__file__).resolve().parents[2] / name)

_FEATURES = [
    ("folder", "一键整理桌面 / 下载等杂乱文件夹"),
    ("sort", "按类型或日期自动分类归拢"),
    ("eye", "整理前生成模拟报告，确认后才执行"),
    ("undo", "每次整理均可一键撤销还原"),
    ("lock", "完全本地运行，文件不上传"),
]


class _UpdateWorker(QThread):
    """Background manifest fetch for the About "检查更新" button.

    Runs off the UI thread so the network call never blocks the dialog. Emits the
    parsed manifest dict, or ``None`` on any failure (fail-closed).
    """

    result = Signal(object)

    def __init__(self, url: str = UPDATE_MANIFEST_URL, parent=None):
        super().__init__(parent)
        self._url = url

    def run(self):  # pragma: no cover - exercised via the event loop in tests
        self.result.emit(fetch_manifest(self._url))


class AboutDialog(QDialog):
    """Product information dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setFixedSize(440, 580)
        self.setModal(True)
        self._checking = False
        self._worker: _UpdateWorker | None = None
        self._latest_manifest: dict | None = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(12)

        name = QLabel(APP_NAME)
        name.setObjectName("about-name")
        version = QLabel(f"版本 {__version__}  ·  {APP_NAME_ZH}")
        version.setObjectName("about-version")

        photo = QLabel()
        photo.setObjectName("about-photo")
        photo.setFixedSize(_PHOTO_SIZE, _PHOTO_SIZE)
        photo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pm = QPixmap(_resource_path("assets/author.jpg"))
        if not pm.isNull():
            pm = pm.scaled(
                _PHOTO_SIZE,
                _PHOTO_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            photo.setPixmap(pm)

        author = QLabel(f"作者：{AUTHOR_NAME}")
        author.setObjectName("about-author")
        wechat = QLabel(f"微信：{CONTACT_WECHAT}")
        wechat.setObjectName("about-author")
        tagline = QLabel(TAGLINE)
        tagline.setObjectName("about-tagline")
        layout.addWidget(name)
        layout.addWidget(version)
        layout.addLayout(self._update_row())
        layout.addWidget(photo, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(author)
        layout.addWidget(wechat)
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

    # ------------------------- update check (E.3) ------------------------ #
    def _update_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        self._check_btn = QPushButton("检查更新")
        self._check_btn.setObjectName("ghost")
        self._check_btn.setMinimumWidth(110)
        self._check_btn.clicked.connect(self._on_check_update)
        row.addWidget(self._check_btn)
        self._update_status = QLabel("")
        self._update_status.setObjectName("about-update-status")
        self._update_status.setWordWrap(True)
        row.addWidget(self._update_status, 1)
        self._download_btn = QPushButton("下载更新")
        self._download_btn.setObjectName("primary")
        self._download_btn.setMinimumWidth(100)
        self._download_btn.clicked.connect(self._on_download)
        self._download_btn.hide()
        row.addWidget(self._download_btn)
        return row

    def _on_check_update(self):
        """IDLE -> CHECKING: start a background fetch (no repeat while busy)."""
        if self._checking:
            return
        self._checking = True
        self._latest_manifest = None
        self._download_btn.hide()
        self._check_btn.setEnabled(False)
        self._check_btn.setText("检查中…")
        self._update_status.setText("")
        self._worker = _UpdateWorker()
        self._worker.result.connect(self._on_update_result)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _on_update_result(self, manifest):
        """CHECKING -> UP_TO_DATE | UPDATE_AVAILABLE | ERROR (fail-closed)."""
        self._checking = False
        self._check_btn.setEnabled(True)
        self._check_btn.setText("检查更新")

        if manifest is None:
            self._set_error("网络连接失败")
            return
        if validate_manifest_basics(manifest) is not None:
            self._set_error("更新信息无效")
            return
        if evaluate(__version__, manifest) == LEVEL_NONE:
            # current >= latest (includes "older manifest" case)
            self._update_status.setText("当前已是最新版本")
            return
        if not is_allowed_download_url(manifest.get("download_url")):
            # update exists but the download URL is unsafe -> never open it
            self._set_error("更新信息无效")
            return
        self._latest_manifest = manifest
        self._update_status.setText(f"发现新版本：{manifest['latest_version']}")
        self._download_btn.show()

    def _on_download(self):
        """User-initiated: open the *validated* download URL only."""
        manifest = self._latest_manifest
        if not manifest:
            return
        url = manifest.get("download_url")
        if not is_allowed_download_url(url):
            return
        QDesktopServices.openUrl(QUrl(url))

    def _set_error(self, reason: str):
        self._update_status.setText("检查更新失败：" + reason)

    @staticmethod
    def _separator() -> QFrame:
        f = QFrame()
        f.setObjectName("separator")
        f.setFrameShape(QFrame.HLine)
        return f
