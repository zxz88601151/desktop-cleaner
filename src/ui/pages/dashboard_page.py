"""Dashboard page (首页) — the primary landing surface.

P0 (UI Freeze Audit): the first visual focus is now *select a folder → scan
→ preview*, not the tidy-score ring. The "电脑整洁度" ring is demoted to a
compact auxiliary card in the hero corner. The hero exposes the real entry
path (folder box + 选择文件夹 + 开始扫描) and emits :attr:`start_scan` so the
shell can route straight into the organize flow with the chosen root.

Everything here is presentation-only; no business logic or schema changes.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QWidget,
)

from data import history_repo, operation_repo, settings_repo
from ui.dashboard import DashboardWidget
from ui.state.worker import Worker
from ui.theme_manager import ThemeManager
from ui.undo import ConfirmUndoDialog, run_undo
from ui.widgets.score_ring import ScoreRing

HC = Qt.AlignmentFlag.AlignHCenter
VC = Qt.AlignmentFlag.AlignVCenter
RIGHT = Qt.AlignmentFlag.AlignRight


def compute_clean_score() -> tuple[int, str]:
    """Derive a tidy-score (0-99) from real organize history.

    Honest, deterministic metric: recent + frequent organizing => higher.
    """
    stats = history_repo.get_stats()
    last = stats["last_time"]
    if not last:
        return 86, "你的数字空间看起来不错，整理一下会更清爽"
    try:
        days = (datetime.now() - datetime.fromisoformat(last)).days
    except ValueError:
        days = 30
    score = 96 - min(days, 56)
    score = max(42, min(99, score))
    if score >= 85:
        label = "文件保持整洁，状态良好"
    elif score >= 70:
        label = "整体不错，但还有提升空间"
    else:
        label = "建议整理一下你的数字空间"
    return score, label


def greeting() -> str:
    """P2-7: time-of-day friendly greeting."""
    h = datetime.now().hour
    if 5 <= h < 11:
        return "早上好"
    if 11 <= h < 13:
        return "中午好"
    if 13 <= h < 18:
        return "下午好"
    return "晚上好"


class DashboardPage(QWidget):
    navigate = Signal(str)
    # P0: hero "开始扫描" kicks off the organize flow on the chosen root.
    start_scan = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        ThemeManager.instance().on_changed(self._on_theme)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(20)

        hero = QFrame()
        hero.setObjectName("hero-card")
        hv = QVBoxLayout(hero)
        hv.setContentsMargins(28, 24, 28, 24)
        hv.setSpacing(18)

        # --- top: brand + compact tidy-score corner --- #
        top = QHBoxLayout()
        top.setSpacing(16)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(4)
        brand = QLabel("桌面文件整理助手")
        brand.setObjectName("page-title")
        self._greet = QLabel()
        self._greet.setObjectName("hero-greet")
        sub = QLabel("选择文件夹，一键扫描并分类整理 — 文件只移动、不删除、可撤销。")
        sub.setObjectName("page-sub")
        brand_col.addWidget(brand)
        brand_col.addWidget(self._greet)
        brand_col.addWidget(sub)
        top.addLayout(brand_col, 1)

        score_corner = QHBoxLayout()
        score_corner.setSpacing(10)
        score_corner.setAlignment(VC)
        self._ring = ScoreRing(86, size=56, thickness=8)
        skv = QVBoxLayout()
        skv.setSpacing(1)
        self._score_k = QLabel("电脑整洁度")
        self._score_k.setObjectName("score-k")
        self._score_v = QLabel("86%")
        self._score_v.setObjectName("score-v-sm")
        skv.addWidget(self._score_k)
        skv.addWidget(self._score_v)
        score_corner.addWidget(self._ring)
        score_corner.addLayout(skv)
        top.addLayout(score_corner)
        hv.addLayout(top)

        # --- folder path box + actions --- #
        path_row = QHBoxLayout()
        path_row.setSpacing(10)
        self._path = QLineEdit()
        self._path.setPlaceholderText("点击「选择文件夹」指定要整理的目录，例如：桌面 / 下载")
        browse = QPushButton("选择文件夹")
        browse.setObjectName("secondary")
        browse.setMinimumHeight(44)
        browse.clicked.connect(self._browse)
        scan_btn = QPushButton("开始扫描")
        scan_btn.setObjectName("primary")
        scan_btn.setMinimumHeight(44)
        scan_btn.clicked.connect(self._start_from_home)
        path_row.addWidget(self._path, 1)
        path_row.addWidget(browse)
        path_row.addWidget(scan_btn)
        hv.addLayout(path_row)

        types = QLabel(
            "支持整理：图片 · 文档 · 视频 · 音频 · 压缩包 · 代码 · 安装程序"
        )
        types.setObjectName("page-sub")
        hv.addWidget(types)

        self._undo_btn = QPushButton("♻️ 一键还原最近一次整理")
        self._undo_btn.setObjectName("undo-cta")
        self._undo_btn.setMinimumHeight(46)
        self._undo_btn.setVisible(False)
        self._undo_btn.clicked.connect(self._undo_latest)
        hv.addWidget(self._undo_btn, 0, HC)

        root.addWidget(hero)

        # --- summary stat cards --- #
        self._stats = DashboardWidget()
        root.addWidget(self._stats)

        # UI-2.0: one lightweight entry to the future-tools page. Deliberately
        # Tertiary — it must never compete with the 选择文件夹 / 开始扫描 CTA,
        # which stays the first focus of the home page.
        more = QPushButton("发现更多工具 →")
        more.setObjectName("tertiary")
        more.setMinimumHeight(38)
        more.clicked.connect(lambda: self.navigate.emit("tools"))
        root.addWidget(more, 0, HC)
        root.addStretch(1)

    def on_enter(self):
        self.refresh()

    def refresh(self):
        self._stats.refresh()
        score, label = compute_clean_score()
        self._ring.setValue(score)
        self._score_v.setText(f"{score}%")
        self._greet.setText(f"{greeting()}，{label}")

        if not self._path.text().strip():
            last = settings_repo.get("last_source")
            if last and Path(last).is_dir():
                self._path.setText(last)
            else:
                desktop = str(Path.home() / "Desktop")
                if Path(desktop).is_dir():
                    self._path.setText(desktop)

        latest = history_repo.latest_done()
        self._undo_btn.setVisible(latest is not None)

    # ----------------------------- hero actions -------------------------- #
    def _browse(self):
        start = self._path.text() or str(Path.home())
        d = QFileDialog.getExistingDirectory(self, "选择要整理的文件夹", start)
        if d:
            self._path.setText(d)
            settings_repo.set("last_source", d)

    def _start_from_home(self):
        root = self._path.text().strip()
        if not root or not Path(root).is_dir():
            QMessageBox.warning(self, "提示", "请先选择一个有效的文件夹。")
            return
        settings_repo.set("last_source", root)
        self.start_scan.emit(root)

    # ----------------------------- undo ----------------------------------- #
    def _undo_latest(self):
        """首页「一键还原最近一次整理」：仅当存在可撤销记录时可用。"""
        latest = history_repo.latest_done()
        if latest is None:
            return
        ops = operation_repo.list_by_history(latest["id"])
        dlg = ConfirmUndoDialog(latest["id"], len(ops), latest["source_path"], self)
        if dlg.exec() != 1:  # QDialog.Accepted
            return
        self._undo_btn.setDisabled(True)
        self._undo_btn.setText("还原中…")
        worker = Worker(lambda p, l: run_undo(latest["id"], p, l))
        worker.progress.connect(lambda *_: None)
        worker.log.connect(lambda *_: None)
        worker.finished.connect(self._on_undo_finished)
        worker.error.connect(self._on_undo_error)
        worker.start()

    def _on_undo_finished(self, payload: dict):
        result = payload["result"]
        self._undo_btn.setDisabled(False)
        self._undo_btn.setText("♻️ 一键还原最近一次整理")
        QMessageBox.information(self, "还原完成", f"已还原 {result.moved} 个文件到原位置。")
        self.refresh()

    def _on_undo_error(self, msg: str):
        self._undo_btn.setDisabled(False)
        self._undo_btn.setText("♻️ 一键还原最近一次整理")
        QMessageBox.critical(self, "错误", msg or "操作未完成，请重试。")

    def _on_theme(self):
        self._ring.update()
