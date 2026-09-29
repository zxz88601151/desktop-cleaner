"""Folder analysis page (文件夹分析) — V1.2-A, feature 2.

Read-only structural analysis of a folder tree:

    选源 -> core.analyze (真实扫描, 只读) -> 概览 + 类型分布 + 排行榜 + 空文件夹

Nothing on this page modifies, moves or deletes anything. The heavy walk runs
on a :class:`Worker` (off the UI thread) and reports progress; the page itself
only renders the already-computed :class:`~core.analysis.AnalysisResult`.

Category labels are produced by :func:`core.rules.category_display` from the
stable keys the analysis layer returns — the data model never carries UI text.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
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

from core import analyze, export
from core.analysis import AnalysisResult
from core.custom_rules import effective_rules
from core.rules import category_display
from data import settings_repo
from ui.icons import category_pixmap, color, pixmap
from ui.state.worker import Worker
from ui.theme_manager import ThemeManager
from utils import human_size
from version import __version__

# How many rows each ranked list renders.
TOP_N = 20


def _fmt_time(ts: float) -> str:
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError, OverflowError):
        return "—"


class AnalysisPage(QWidget):
    navigate = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._worker: Worker | None = None
        self._root: str | None = None
        self._result: AnalysisResult | None = None
        # The effective rule set used for the analysis that produced _result.
        # Kept so the exported report records the SAME rules_version the
        # categories were actually computed with (V1.2-A F4).
        self._rules_used: dict = {}
        self._build()
        ThemeManager.instance().on_changed(self._on_theme)

    # ----------------------------- build --------------------------------- #
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        title = QLabel("文件夹分析")
        title.setObjectName("page-title")
        sub = QLabel("看清一个文件夹的空间占用与内容构成 — 只读分析，不修改任何文件")
        sub.setObjectName("page-sub")
        root.addWidget(title)
        root.addWidget(sub)

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

        self._scan_btn = QPushButton("开始分析")
        self._scan_btn.setObjectName("primary")
        self._scan_btn.setMinimumHeight(44)
        self._scan_btn.clicked.connect(self._start_scan)
        cv.addWidget(self._scan_btn)
        root.addWidget(card)

        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._status = QLabel("")
        self._status.setObjectName("page-sub")
        self._status.setVisible(False)
        root.addWidget(self._progress)
        root.addWidget(self._status)

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
        self._load_settings()

    def _show_empty_stage(self):
        self._clear_stage()
        hint = QLabel(
            "选择文件夹后点击「开始分析」，将展示总大小、文件与文件夹数量、"
            "类型分布、最大的文件 / 文件夹、最近修改的文件，以及空文件夹。"
        )
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

    # ----------------------------- settings ------------------------------- #
    def _load_settings(self):
        last = settings_repo.get("last_source")
        if last and Path(last).is_dir():
            self._source.setText(last)
        else:
            desktop = str(Path.home() / "Desktop")
            if Path(desktop).is_dir():
                self._source.setText(desktop)

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

    # ----------------------------- scan ----------------------------------- #
    def _start_scan(self):
        root = self._valid_root()
        if root is None or self._busy():
            return
        self._root = root
        settings_repo.set("last_source", root)
        self._set_busy(True)
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)  # indeterminate until ticks arrive
        self._status.setVisible(True)
        self._status.setText(f"正在分析：{root} …")
        self._show_empty_stage()
        # Resolve the rules ONCE on the UI thread, then hand the same dict to
        # the worker and keep it for the report — so categorisation and the
        # exported rules_version can never disagree.
        rules = effective_rules()
        self._rules_used = rules
        self._worker = Worker(lambda p, l: self._task_scan(root, rules, p, l))
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_scan_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    @staticmethod
    def _task_scan(root, rules, p, l):
        result = analyze(root, rules=rules, top_n=TOP_N, on_progress=p)
        l(f"分析完成：{result.file_count} 个文件 / {result.folder_count} 个文件夹")
        return result

    def _on_scan_done(self, result: AnalysisResult):
        self._set_busy(False)
        self._progress.setVisible(False)
        self._result = result
        if result.file_count == 0 and result.folder_count == 0:
            self._status.setText("分析完成：该文件夹为空")
            self._show_empty_stage()
            return
        extra = ""
        if result.skipped:
            extra = f" · 跳过 {result.skipped} 个无法读取或链接项"
        self._status.setText(
            f"分析完成：{result.file_count} 个文件 · {human_size(result.total_size)}"
            f" · 用时 {result.duration_ms} ms{extra}"
        )
        self._render(result)

    # ----------------------------- render --------------------------------- #
    def _add_section(self, title: str) -> QVBoxLayout:
        """Append a titled panel and return its content layout."""
        head = QLabel(title)
        head.setObjectName("section-title")
        self._stage_lay.addWidget(head)
        panel = QFrame()
        panel.setObjectName("panel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)
        self._stage_lay.addWidget(panel)
        return lay

    def _render(self, r: AnalysisResult):
        self._clear_stage()

        # ---- overview stat cards ---- #
        stats = QHBoxLayout()
        stats.setSpacing(12)
        stats.addWidget(self._stat("总大小", human_size(r.total_size), "archive"))
        stats.addWidget(self._stat("文件数", str(r.file_count), "document"))
        stats.addWidget(self._stat("文件夹数", str(r.folder_count), "folder"))
        wrap = QWidget()
        wrap.setLayout(stats)
        self._stage_lay.addWidget(wrap)

        # ---- export actions ---- #
        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch(1)
        export_btn = QPushButton("导出报告")
        export_btn.setObjectName("secondary")
        export_btn.clicked.connect(self._export)
        actions.addWidget(export_btn)
        aw = QWidget()
        aw.setLayout(actions)
        self._stage_lay.addWidget(aw)

        # ---- category distribution ---- #
        if r.by_category:
            lay = self._add_section("类型分布")
            max_count = max(r.by_category.values()) or 1
            for key, count in r.by_category.items():
                label = category_display(key)
                size = human_size(r.by_category_size.get(key, 0))
                row = QFrame()
                row.setObjectName("cat-row")
                rv = QVBoxLayout(row)
                rv.setContentsMargins(14, 12, 14, 12)
                rv.setSpacing(8)
                top = QHBoxLayout()
                top.setSpacing(10)
                ic = QLabel()
                ic.setObjectName("cat-emoji")
                ic.setFixedSize(24, 24)
                ic.setPixmap(category_pixmap(label, color("text_secondary"), 24))
                nm = QLabel(label)
                nm.setObjectName("cat-name")
                cnt = QLabel(f"{count} 个 · {size}")
                cnt.setObjectName("tl-sub")
                top.addWidget(ic)
                top.addWidget(nm)
                top.addStretch(1)
                top.addWidget(cnt)
                bar = QFrame()
                bar.setObjectName("cat-bar")
                blay = QHBoxLayout(bar)
                blay.setContentsMargins(0, 0, 0, 0)
                blay.setSpacing(0)
                fill = QFrame()
                fill.setObjectName("cat-bar-fill")
                blay.addWidget(fill, count)
                blay.addStretch(max_count - count)
                rv.addLayout(top)
                rv.addWidget(bar)
                lay.addWidget(row)

        # ---- largest files ---- #
        if r.largest_files:
            lay = self._add_section(f"最大的文件（前 {len(r.largest_files)} 个）")
            for i, f in enumerate(r.largest_files, 1):
                lay.addWidget(self._rank_row(i, f.name, human_size(f.size), str(f.path.parent)))

        # ---- largest folders ---- #
        if r.largest_folders:
            lay = self._add_section(f"最大的文件夹（前 {len(r.largest_folders)} 个）")
            for i, d in enumerate(r.largest_folders, 1):
                sub = f"{d.file_count} 个文件 · {d.folder_count} 个子文件夹"
                lay.addWidget(
                    self._rank_row(i, d.name, human_size(d.total_size), f"{d.path}\n{sub}")
                )

        # ---- recent files ---- #
        if r.recent_files:
            lay = self._add_section(f"最近修改的文件（前 {len(r.recent_files)} 个）")
            for f in r.recent_files:
                lay.addWidget(
                    self._rank_row(None, f.name, _fmt_time(f.mtime), str(f.path.parent))
                )

        # ---- empty folders ---- #
        lay = self._add_section("空文件夹")
        if r.empty_folders:
            info = QLabel(f"发现 {len(r.empty_folders)} 个空文件夹，可前往「空文件夹清理」处理。")
            info.setObjectName("tl-sub")
            info.setWordWrap(True)
            lay.addWidget(info)
            preview = "\n".join(r.empty_folders[:10])
            more = f"\n… 其余 {len(r.empty_folders) - 10} 个" if len(r.empty_folders) > 10 else ""
            pl = QLabel(preview + more)
            pl.setObjectName("cat-ext")
            pl.setWordWrap(True)
            lay.addWidget(pl)
            go = QPushButton("去清理空文件夹")
            go.setObjectName("ghost")
            go.clicked.connect(lambda: self.navigate.emit("empty"))
            row = QHBoxLayout()
            row.addWidget(go)
            row.addStretch(1)
            lay.addLayout(row)
        else:
            none = QLabel("没有发现空文件夹。")
            none.setObjectName("tl-sub")
            lay.addWidget(none)

        self._stage_lay.addStretch(1)

    def _stat(self, label: str, value: str, icon_name: str) -> QFrame:
        card = QFrame()
        card.setObjectName("cat-box")
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 16, 16, 16)
        v.setSpacing(4)
        ic = QLabel()
        ic.setObjectName("stat-icon")
        ic.setPixmap(pixmap(icon_name, color("accent"), 24))
        val = QLabel(value)
        val.setObjectName("stat-value")
        lab = QLabel(label)
        lab.setObjectName("stat-label")
        v.addWidget(ic)
        v.addWidget(val)
        v.addWidget(lab)
        return card

    def _rank_row(self, rank, name: str, right: str, sub: str) -> QFrame:
        row = QFrame()
        row.setObjectName("cat-row")
        rv = QVBoxLayout(row)
        rv.setContentsMargins(14, 12, 14, 12)
        rv.setSpacing(6)
        top = QHBoxLayout()
        top.setSpacing(10)
        if rank is not None:
            rl = QLabel(str(rank))
            rl.setStyleSheet(
                f"font-weight:700; color:{color('accent')}; min-width:26px;"
            )
            top.addWidget(rl)
        nm = QLabel(name)
        nm.setObjectName("tl-title")
        val = QLabel(right)
        val.setObjectName("summary-line")
        val.setStyleSheet(f"color:{color('accent')};")
        top.addWidget(nm, 1)
        top.addWidget(val)
        ds = QLabel(sub)
        ds.setObjectName("tl-sub")
        ds.setWordWrap(True)
        rv.addLayout(top)
        rv.addWidget(ds)
        return row

    # ----------------------------- export --------------------------------- #
    def _export(self):
        """Export the current analysis result as JSON or CSV.

        The report is built by :func:`core.report.export` — the UI only picks a
        path and reports the outcome. Nothing here formats data by hand.
        """
        if self._result is None:
            QMessageBox.information(self, "导出报告", "请先完成一次分析。")
            return
        stem = f"文件夹分析报告_{Path(self._result.root).name or 'root'}"
        # strip characters Windows forbids in a file name
        stem = "".join(c for c in stem if c not in '<>:"/\\|?*') or "文件夹分析报告"
        start_dir = self._source.text().strip() or str(Path.home())
        start = str(Path(start_dir) / f"{stem}.json")
        path, selected = QFileDialog.getSaveFileName(
            self,
            "导出分析报告",
            start,
            "JSON 报告 (*.json);;CSV 表格 (*.csv)",
        )
        if not path:
            return
        out_path = Path(path)
        if out_path.suffix.lower() not in (".json", ".csv"):
            # no/unknown extension -> follow the filter the user chose
            out_path = out_path.with_suffix(
                ".csv" if selected.strip().startswith("CSV") else ".json"
            )
        try:
            written = export(
                self._result,
                out_path,
                app_version=__version__,
                rules=self._rules_used or None,
            )
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "导出失败", f"无法写入报告：\n{exc}")
            return

        box = QMessageBox(self)
        box.setWindowTitle("导出完成")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(f"报告已导出：\n{written}")
        open_btn = box.addButton("打开所在文件夹", QMessageBox.ButtonRole.ActionRole)
        box.addButton("好", QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        if box.clickedButton() is open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(written.parent)))

    # ----------------------------- busy / progress ------------------------ #
    def _busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def _set_busy(self, busy: bool):
        self._source.setDisabled(busy)
        self._scan_btn.setDisabled(busy)

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
        self._status.setText("分析失败")
        QMessageBox.critical(self, "错误", msg or "分析未完成，请重试。")

    def _on_theme(self):
        # Re-render so icon/accent colours follow the theme switch.
        if self._result is not None:
            self._render(self._result)

    def on_enter(self):
        self._load_settings()
