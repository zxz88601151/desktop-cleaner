"""Large files page (大文件分析) — discover the biggest files in a folder.

PHASE 1.2 (LARGE FILE DISCOVERY). Discovery-only, per the locked Scope:

  - Reuses :func:`core.scanner.scan` so every existing safety filter already
    applies (hidden / system files / already-organized output dirs / the app's
    own data directory guard).
  - File sizes come from ``ScanResult.sizes``, captured during the single stat
    pass of the scanner — no second stat, no database, no index service.
  - Results are sorted by *real byte size* (not formatted strings) descending,
    and only the top-``TOP_N`` rows are rendered to avoid UI jank on huge
    folders (audit report §H).
  - The only file action is *打开所在位置* (reveal the file in Explorer).
    Nothing here deletes, cleans or moves any file.

Exposes a pure, UI-free helper :func:`collect_large_files` so the sorting /
top-N behaviour can be unit-tested directly.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core import classify, scan
from core.rules import category_display
from core.scanner import ScanResult
from data import settings_repo
from ui.icons import color
from ui.state.worker import Worker
from ui.theme_manager import ThemeManager
from ui.widgets.controls import ToggleSwitch
from utils import human_size

# Only the largest N files are rendered (audit §H). The scan still counts all.
TOP_N = 100


def collect_large_files(
    result: ScanResult, limit: int = TOP_N
) -> list[tuple[Path, int]]:
    """Return ``(path, size_bytes)`` entries sorted by size descending, capped.

    - Sorting key is the real byte size (never the formatted string).
    - Equal sizes are broken by ascending path string (deterministic order).
    - A missing size entry (defensive) is treated as 0 bytes, so a failed
      stat never crashes the discovery.
    """
    entries = [(f, result.sizes.get(str(f), 0)) for f in result.files]
    entries.sort(key=lambda t: (-t[1], str(t[0])))
    return entries[:limit]


class LargeFilesPage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._worker: Worker | None = None
        self._root: str | None = None
        self._recursive = False
        self._build()
        ThemeManager.instance().on_changed(self._on_theme)

    # ----------------------------- build --------------------------------- #
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        self._title = QLabel("大文件分析")
        self._title.setObjectName("page-title")
        self._sub = QLabel("扫描并查看当前文件夹中占用空间较大的文件 — 只查看，不删除")
        self._sub.setObjectName("page-sub")
        root.addWidget(self._title)
        root.addWidget(self._sub)

        # ---- config card ---- #
        card = QFrame()
        card.setObjectName("step-card")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(22, 22, 22, 22)
        cv.setSpacing(14)

        fl = QLabel("分析文件夹")
        fl.setObjectName("field-label")
        cv.addWidget(fl)

        src_row = QHBoxLayout()
        src_row.setSpacing(10)
        self._source = QLineEdit()
        self._source.setPlaceholderText("点击右侧按钮选择要分析的文件夹，例如：桌面 / 下载")
        browse = QPushButton("选择文件夹")
        browse.setObjectName("secondary")
        browse.clicked.connect(self._browse)
        src_row.addWidget(self._source, 1)
        src_row.addWidget(browse)
        cv.addLayout(src_row)

        opt_row = QHBoxLayout()
        opt_row.setSpacing(14)
        self._recursive_toggle = ToggleSwitch(False)
        self._recursive_toggle.toggled.connect(self._on_recursive)
        rec_label = QLabel("包含子文件夹")
        rec_label.setObjectName("tl-sub")
        opt_row.addWidget(self._recursive_toggle)
        opt_row.addWidget(rec_label)
        opt_row.addStretch(1)
        cv.addLayout(opt_row)

        self._scan_btn = QPushButton("开始扫描")
        self._scan_btn.setObjectName("primary")
        self._scan_btn.setMinimumHeight(44)
        self._scan_btn.clicked.connect(self._start_scan)
        cv.addWidget(self._scan_btn)
        root.addWidget(card)

        # ---- progress / status ---- #
        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._status = QLabel("")
        self._status.setObjectName("page-sub")
        self._status.setVisible(False)
        root.addWidget(self._progress)
        root.addWidget(self._status)

        # ---- results ---- #
        self._stage = QScrollArea()
        self._stage.setWidgetResizable(True)
        self._stage.setFrameShape(QFrame.Shape.NoFrame)
        self._stage.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._stage_widget = QWidget()
        self._stage_lay = QVBoxLayout(self._stage_widget)
        self._stage_lay.setContentsMargins(0, 0, 0, 0)
        self._stage_lay.setSpacing(10)
        self._stage.setWidget(self._stage_widget)
        root.addWidget(self._stage, 1)

        self._show_empty_stage()

        # initial source from settings
        self._load_settings()

    def _show_empty_stage(self):
        self._clear_stage()
        hint = QLabel("选择文件夹后点击「开始扫描」，将按文件大小从大到小展示最大的文件。")
        hint.setObjectName("page-sub")
        hint.setWordWrap(True)
        self._stage_lay.addWidget(hint)
        self._stage_lay.addStretch(1)

    def _clear_stage(self):
        while self._stage_lay.count():
            item = self._stage_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

    # ----------------------------- settings ------------------------------ #
    def _load_settings(self):
        last = settings_repo.get("last_source")
        if last and Path(last).is_dir():
            self._source.setText(last)
        else:
            desktop = str(Path.home() / "Desktop")
            if Path(desktop).is_dir():
                self._source.setText(desktop)
        self._recursive = bool(int(settings_repo.get("recursive", 0) or 0))
        self._recursive_toggle.set_on(self._recursive, silent=True)

    def _on_recursive(self, on: bool):
        self._recursive = on
        settings_repo.set("recursive", int(on))

    # ----------------------------- browse -------------------------------- #
    def _browse(self):
        start = self._source.text() or str(Path.home())
        d = QFileDialog.getExistingDirectory(self, "选择要分析的文件夹", start)
        if d:
            self._source.setText(d)
            settings_repo.set("last_source", d)

    def _valid_root(self) -> str | None:
        root = self._source.text().strip()
        if not root or not Path(root).is_dir():
            QMessageBox.warning(self, "提示", "请先选择一个有效的文件夹。")
            return None
        return root

    # ----------------------------- scan ---------------------------------- #
    def _start_scan(self):
        root = self._valid_root()
        if root is None or self._busy():
            return
        self._root = root
        self._set_busy(True)
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)  # indeterminate
        self._status.setVisible(True)
        self._status.setText(f"正在扫描：{root} …")
        self._worker = Worker(
            lambda p, l: self._task_scan(root, self._recursive, p, l)
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_scan_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    @staticmethod
    def _task_scan(root, recursive, p, l):
        result = scan(Path(root), mode="type", recursive=recursive)
        l(f"扫描到 {result.total} 个文件")
        return result

    def _on_scan_done(self, result: ScanResult):
        self._set_busy(False)
        self._progress.setVisible(False)
        entries = collect_large_files(result, TOP_N)
        if not entries:
            self._status.setText(f"扫描完成：{result.total} 个文件 · 没有可展示的文件")
            self._show_empty_stage()
            return
        self._status.setText(
            f"扫描完成：{result.total} 个文件 · 共 {human_size(result.total_size)}"
            f" · 展示前 {len(entries)} 个最大的文件"
        )
        self._render_entries(entries)

    def _render_entries(self, entries: list[tuple[Path, int]]):
        self._clear_stage()
        for i, (path, size) in enumerate(entries, 1):
            row = QFrame()
            row.setObjectName("cat-row")
            rv = QVBoxLayout(row)
            rv.setContentsMargins(14, 12, 14, 12)
            rv.setSpacing(6)

            top = QHBoxLayout()
            top.setSpacing(10)
            rank = QLabel(str(i))
            rank.setStyleSheet(f"font-weight:700; color:{color('accent')}; min-width:26px;")
            nm = QLabel(path.name)
            nm.setObjectName("tl-title")
            sz = QLabel(human_size(size))
            sz.setObjectName("summary-line")
            sz.setStyleSheet(f"color:{color('accent')};")
            top.addWidget(rank)
            top.addWidget(nm, 1)
            top.addWidget(sz)

            sub = QLabel(self._path_line(path))
            sub.setObjectName("tl-sub")
            sub.setWordWrap(True)

            act = QHBoxLayout()
            act.setSpacing(10)
            typ = QLabel(f"类型：{category_display(classify(path))}")
            typ.setObjectName("tl-sub")
            reveal = QPushButton("打开位置")
            reveal.setObjectName("ghost")
            reveal.clicked.connect(
                lambda _=False, p=str(path): self._reveal(p)
            )
            act.addWidget(typ)
            act.addStretch(1)
            act.addWidget(reveal)

            rv.addLayout(top)
            rv.addWidget(sub)
            rv.addLayout(act)
            self._stage_lay.addWidget(row)
        self._stage_lay.addStretch(1)

    @staticmethod
    def _path_line(path: Path) -> str:
        """Show the folder containing the file (compact display)."""
        try:
            return str(path.parent)
        except Exception:  # noqa: BLE001 - display-only fallback
            return str(path)

    # ----------------------------- file action --------------------------- #
    @staticmethod
    def _reveal(path: str):
        """Open the file's location. Windows Explorer selects the file."""
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", "/select,", str(Path(path))])
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).parent)))
        except Exception:  # noqa: BLE001 - reveal must never crash the page
            QMessageBox.warning(
                None, "提示", f"无法打开文件位置：{Path(path).name}"
            )

    # ----------------------------- busy / progress ----------------------- #
    def _busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def _set_busy(self, busy: bool):
        self._source.setDisabled(busy)
        self._scan_btn.setDisabled(busy)
        self._recursive_toggle.setDisabled(busy)

    def _on_progress(self, cur: int, total: int, msg: str):
        if total and total > 0:
            self._progress.setRange(0, total)
            self._progress.setValue(cur)
        self._status.setText(msg)

    def _on_log(self, msg: str):
        self._status.setText(msg)

    def _on_error(self, msg: str):
        self._set_busy(False)
        self._progress.setVisible(False)
        self._status.setText("扫描失败")
        QMessageBox.critical(self, "错误", msg or "扫描未完成，请重试。")

    def _on_theme(self):
        self._recursive_toggle.update()

    def on_enter(self):
        self._load_settings()
