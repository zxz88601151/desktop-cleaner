"""Organize page (智能整理) — the core working surface.

Wires the real business layer end-to-end:

  选源 -> core.scan (真实扫描) -> 生成方案 (core.plan + summarize_plan)
       -> PreviewReportDialog (安全门, 保留测试契约)
       -> core.organize (严格 4 步: history_repo.create -> organize
          -> operation_repo.bulk_insert -> history_repo.update_status)
       -> 完成态

All off-UI-thread work runs through :class:`ui.state.worker.Worker`.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
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

from core import plan, scan, summarize_plan, move_items
from core.organizer import OrganizeResult
from core.rules import DEFAULT_RULES, category_display
from core.scanner import ScanResult
from data import history_repo, operation_repo, settings_repo
from ui.icons import category_pixmap, color, pixmap
from ui.preview_report import PreviewReportDialog
from ui.state.worker import Worker
from ui.theme_manager import ThemeManager
from ui.undo import ConfirmUndoDialog, run_undo
from ui.widgets.controls import Segmented, ToggleSwitch
from utils import human_size

# P1-3: read-only reverse-map of category display label -> supported extensions.
# Derived from DEFAULT_RULES (ext -> key) + category_display; no rule changes.
_EXT_BY_LABEL: dict[str, list[str]] = {}
for _ext, _key in DEFAULT_RULES.items():
    _EXT_BY_LABEL.setdefault(category_display(_key), []).append(_ext)


class OrganizePage(QWidget):
    navigate = Signal(str)
    finished = Signal()  # emitted after a successful organize run

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._worker: Worker | None = None
        self._root: str | None = None
        self._mode = "type"
        self._recursive = False
        self._scan_result: ScanResult | None = None
        self._last_hid: int | None = None
        self._failed_details: list = []
        self._build()
        ThemeManager.instance().on_changed(self._on_theme)

    # ----------------------------- build --------------------------------- #
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        self._title = QLabel("整理")
        self._title.setObjectName("page-title")
        self._sub = QLabel("扫描 · 分类 · 整理 · 可撤销 — 文件只移动、不删除")
        self._sub.setObjectName("page-sub")
        root.addWidget(self._title)
        root.addWidget(self._sub)

        # ---- config card ---- #
        card = QFrame()
        card.setObjectName("step-card")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(22, 22, 22, 22)
        cv.setSpacing(14)

        fl = QLabel("整理文件夹")
        fl.setObjectName("field-label")
        cv.addWidget(fl)

        src_row = QHBoxLayout()
        src_row.setSpacing(10)
        self._source = QLineEdit()
        self._source.setPlaceholderText("点击右侧按钮选择要整理的文件夹，例如：桌面 / 下载")
        browse = QPushButton("选择文件夹")
        browse.setObjectName("secondary")
        browse.clicked.connect(self._browse)
        src_row.addWidget(self._source, 1)
        src_row.addWidget(browse)
        cv.addLayout(src_row)

        mode_label = QLabel("整理方式")
        mode_label.setObjectName("field-label")
        cv.addWidget(mode_label)

        opt_row = QHBoxLayout()
        opt_row.setSpacing(14)
        self._mode_seg = Segmented([("type", "按类型"), ("date", "按日期")])
        self._mode_seg.selected.connect(self._on_mode)
        self._recursive_toggle = ToggleSwitch(False)
        self._recursive_toggle.toggled.connect(self._on_recursive)
        rec_label = QLabel("包含子文件夹")
        rec_label.setObjectName("tl-sub")
        opt_row.addWidget(self._mode_seg)
        opt_row.addStretch(1)
        opt_row.addWidget(self._recursive_toggle)
        opt_row.addWidget(rec_label)
        cv.addLayout(opt_row)

        self._scan_btn = QPushButton("开始扫描")
        self._scan_btn.setObjectName("primary")
        self._scan_btn.setMinimumHeight(44)
        self._scan_btn.clicked.connect(self._start_scan)
        cv.addWidget(self._scan_btn)
        root.addWidget(card)

        # ---- progress (scan / execute) ---- #
        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._status = QLabel("")
        self._status.setObjectName("page-sub")
        self._status.setVisible(False)
        root.addWidget(self._progress)
        root.addWidget(self._status)

        # ---- stage (empty / preview / done) ---- #
        self._stage = QScrollArea()
        self._stage.setWidgetResizable(True)
        self._stage.setFrameShape(QFrame.Shape.NoFrame)
        self._stage.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._stage_widget = QWidget()
        self._stage_lay = QVBoxLayout(self._stage_widget)
        self._stage_lay.setContentsMargins(0, 0, 0, 0)
        self._stage_lay.setSpacing(16)
        self._stage.setWidget(self._stage_widget)
        root.addWidget(self._stage, 1)

        self._build_preview_stage()
        self._build_done_stage()
        self._show_empty_stage()

        # initial control values from settings
        self._load_settings()

    def _build_preview_stage(self):
        self._preview = QWidget()
        pv = QVBoxLayout(self._preview)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(14)

        self._summary = QLabel()
        self._summary.setObjectName("summary-line")
        pv.addWidget(self._summary)

        self._preview_list = QFrame()
        self._preview_list.setObjectName("panel")
        self._preview_list_lay = QVBoxLayout(self._preview_list)
        self._preview_list_lay.setContentsMargins(8, 8, 8, 8)
        self._preview_list_lay.setSpacing(8)
        pv.addWidget(self._preview_list, 1)

        self._plan_btn = QPushButton("开始整理")
        self._plan_btn.setObjectName("primary")
        self._plan_btn.setMinimumHeight(44)
        self._plan_btn.clicked.connect(self._plan_and_preview)
        pv.addWidget(self._plan_btn)

    def _build_done_stage(self):
        self._done = QWidget()
        dv = QVBoxLayout(self._done)
        dv.setContentsMargins(0, 12, 0, 0)
        dv.setSpacing(12)
        dv.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._done_emoji = QLabel()
        self._done_emoji.setObjectName("done-ico")
        self._done_emoji.setFixedSize(46, 46)
        self._done_emoji.setPixmap(pixmap("check", color("success"), 46))
        self._done_emoji.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._done_title = QLabel("整理完成")
        self._done_title.setObjectName("result-title")
        self._done_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._done_sub = QLabel()
        self._done_sub.setObjectName("result-sub")
        self._done_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dv.addWidget(self._done_emoji)
        dv.addWidget(self._done_title)
        dv.addWidget(self._done_sub)
        self._done_cats = QLabel()
        self._done_cats.setObjectName("result-sub")
        self._done_cats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._done_cats.setWordWrap(True)
        dv.addWidget(self._done_cats)
        dv.addSpacing(10)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.setSpacing(12)
        restore_btn = QPushButton("一键还原本次整理")
        restore_btn.setObjectName("undo-cta")
        restore_btn.setMinimumHeight(44)
        restore_btn.clicked.connect(self._undo_this)
        home_btn = QPushButton("返回首页")
        home_btn.setObjectName("primary")
        home_btn.clicked.connect(lambda: self.navigate.emit("home"))
        hist_btn = QPushButton("查看历史")
        hist_btn.setObjectName("ghost")
        hist_btn.clicked.connect(lambda: self.navigate.emit("history"))
        again_btn = QPushButton("再整理一次")
        again_btn.setObjectName("tertiary")
        again_btn.clicked.connect(self._reset_to_config)
        btn_row.addWidget(restore_btn)
        btn_row.addWidget(home_btn)
        btn_row.addWidget(hist_btn)
        btn_row.addWidget(again_btn)
        dv.addLayout(btn_row)

        # P1-4: let the user inspect *why* individual files failed.
        self._detail_btn = QPushButton("查看失败明细")
        self._detail_btn.setObjectName("ghost")
        self._detail_btn.setVisible(False)
        self._detail_btn.clicked.connect(self._show_failed_details)
        dv.addWidget(self._detail_btn)

    def _show_empty_stage(self):
        # clear stage widget, add a hint label
        self._clear_stage()
        hint = QLabel("选择文件夹后点击「开始扫描」，我们会先预览再整理。")
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

    def _set_stage(self, widget: QWidget):
        self._clear_stage()
        self._stage_lay.addWidget(widget, 1)
        self._stage_lay.addStretch(1)

    # ----------------------------- settings ------------------------------ #
    def _load_settings(self):
        last = settings_repo.get("last_source")
        if last and Path(last).is_dir():
            self._source.setText(last)
        else:
            desktop = str(Path.home() / "Desktop")
            if Path(desktop).is_dir():
                self._source.setText(desktop)
        mode = settings_repo.get("mode", "type")
        if mode in ("type", "date"):
            self._mode_seg.set_value(mode)
            self._mode = mode
        self._recursive = bool(int(settings_repo.get("recursive", 0) or 0))
        self._recursive_toggle.set_on(self._recursive, silent=True)

    def _on_mode(self, mode: str):
        self._mode = mode
        settings_repo.set("mode", mode)

    def _on_recursive(self, on: bool):
        self._recursive = on
        settings_repo.set("recursive", int(on))

    # ----------------------------- browse -------------------------------- #
    def _browse(self):
        start = self._source.text() or str(Path.home())
        d = QFileDialog.getExistingDirectory(self, "选择要整理的文件夹", start)
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
        self._mode = self._mode_seg.value() or "type"
        settings_repo.set("mode", self._mode)
        self._set_busy(True)
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)  # indeterminate
        self._status.setVisible(True)
        self._status.setText(f"正在扫描：{root} …")
        self._worker = Worker(
            lambda p, l: self._task_scan(root, self._mode, self._recursive, p, l)
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_scan_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    @staticmethod
    def _task_scan(root, mode, recursive, p, l):
        result = scan(Path(root), mode=mode, recursive=recursive)
        l(f"扫描到 {result.total} 个文件")
        return result

    def _on_scan_done(self, result: ScanResult):
        self._scan_result = result
        self._render_preview(result)
        self._set_busy(False)
        self._progress.setVisible(False)
        self._status.setText(
            f"扫描完成：{result.total} 个文件 · {human_size(result.total_size)}"
        )

    def _render_preview(self, result: ScanResult):
        # clear preview list
        while self._preview_list_lay.count():
            item = self._preview_list_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

        cats = sorted(result.by_category.items(), key=lambda kv: kv[1], reverse=True)
        max_count = max((c for _, c in cats), default=1) or 1
        for label, count in cats:
            size = human_size(result.by_category_size.get(label, 0))
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
            exts = _EXT_BY_LABEL.get(label, [])
            if exts:
                ext_line = QLabel("常见扩展名：" + " · ".join(sorted(exts)[:10]))
                ext_line.setObjectName("cat-ext")
                rv.addWidget(ext_line)
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
            self._preview_list_lay.addWidget(row)

        self._summary.setText(
            f"共 {result.total} 个文件 · {human_size(result.total_size)}，"
            f"建议分为 {len(cats)} 类"
        )
        self._set_stage(self._preview)

    # ----------------------------- plan ----------------------------------- #
    def _plan_and_preview(self):
        if self._root is None or self._busy():
            return
        self._set_busy(True)
        self._status.setVisible(True)
        self._status.setText("正在生成整理方案…")
        self._worker = Worker(
            lambda p, l: self._task_plan(self._root, self._mode, self._recursive, p, l)
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_plan_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    @staticmethod
    def _task_plan(root, mode, recursive, p, l):
        items = plan(Path(root), mode=mode, recursive=recursive)
        l(f"已规划 {len(items)} 个文件的移动")
        return summarize_plan(items, Path(root))

    def _on_plan_done(self, report: dict):
        self._set_busy(False)
        self._status.setText(
            f"模拟报告：{report['total']} 个文件 · {human_size(report['total_size'])}"
        )
        if report["total"] == 0:
            QMessageBox.information(self, "提示", "没有需要整理的文件。")
            return
        report["mode"] = self._mode
        dlg = PreviewReportDialog(report, self)
        if dlg.exec() == 1:  # QDialog.Accepted
            self._run_organize()
        else:
            self._status.setText("已取消整理")

    # ----------------------------- execute -------------------------------- #
    def _run_organize(self):
        if self._root is None or self._busy():
            return
        self._set_busy(True)
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        self._status.setVisible(True)
        self._status.setText("开始整理…")
        self._worker = Worker(
            lambda p, l: self._task_organize(self._root, self._mode, self._recursive, p, l)
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_organize_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    @staticmethod
    def _task_organize(root, mode, recursive, p, l):
        # P0-1 严格顺序：先落库 pending -> 移动+校验 -> 更新 moved/failed
        hid = history_repo.create(root, mode, 0)
        l(f"已创建整理记录 #{hid}")
        items = plan(Path(root), mode=mode, recursive=recursive)
        operation_repo.bulk_insert_pending(hid, items)  # 移动前记录 pending
        result = move_items(items, on_progress=p)        # 移动 + 逐文件校验
        moved_targets = {str(it.target) for it in result.items}
        failed_targets = {str(it.target) for it in result.failed_items}
        operation_repo.update_statuses_by_target(hid, moved_targets, failed_targets)
        history_repo.update_status(hid, "done", result.moved, result.skipped)
        return {"hid": hid, "result": result}

    def _on_organize_done(self, payload: dict):
        result: OrganizeResult = payload["result"]
        self._last_hid = payload["hid"]
        self._set_busy(False)
        self._progress.setVisible(False)
        if result.failed:
            self._status.setText(
                f"整理完成：移动 {result.moved} 个，失败 {result.failed} 个"
            )
            self._failed_details = getattr(result, "failed_details", [])
            self._detail_btn.setVisible(bool(self._failed_details))
        else:
            self._status.setText(f"整理完成：移动 {result.moved} 个文件")
            self._failed_details = []
            self._detail_btn.setVisible(False)
        self._done_sub.setText(
            f"已移动 {result.moved} 个文件到分类文件夹。"
            "如需恢复，可在「整理历史」中撤销。"
        )
        # P2-6: show the category breakdown derived from result.items.
        counts: dict[str, int] = {}
        for it in result.items:
            counts[it.category] = counts.get(it.category, 0) + 1
        if counts:
            parts = [
                f"{lbl}：{n}"
                for lbl, n in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
            ]
            self._done_cats.setText(" · ".join(parts))
        else:
            self._done_cats.setText("")
        self._set_stage(self._done)
        self.finished.emit()

    def _show_failed_details(self):
        """P1-4: surface the structured failure list to the user."""
        if not self._failed_details:
            return
        lines = []
        for d in self._failed_details:
            name = Path(d.get("source", "")).name
            lines.append(f"• {name}\n  原因：{d.get('error_message', '')}")
        QMessageBox.warning(
            self, "失败明细", "\n".join(lines) or "无失败记录。"
        )

    # ----------------------------- one-click undo ------------------------- #
    def _undo_this(self):
        """完成页「一键还原本次整理」：确认后走同一套 5 步撤销。"""
        if self._last_hid is None or self._busy():
            return
        rec = history_repo.get(self._last_hid)
        if rec is None or rec["status"] != "done":
            return
        ops = operation_repo.list_by_history(self._last_hid)
        dlg = ConfirmUndoDialog(self._last_hid, len(ops), rec["source_path"], self)
        if dlg.exec() != 1:  # QDialog.Accepted
            return
        self._set_busy(True)
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        self._status.setVisible(True)
        self._status.setText("正在还原本次整理…")
        self._worker = Worker(
            lambda p, l: run_undo(self._last_hid, p, l)
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_undo_done_redirect)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_undo_done_redirect(self, payload: dict):
        result: OrganizeResult = payload["result"]
        failed_files = payload.get("failed_files") or []
        self._set_busy(False)
        self._progress.setVisible(False)
        if failed_files:
            self._status.setText(f"还原 {result.moved} 个，失败 {len(failed_files)} 个")
            detail = "\n".join(failed_files[:10])
            QMessageBox.warning(
                self,
                "还原未完成",
                f"已还原 {result.moved} 个文件，{len(failed_files)} 个还原失败：\n{detail}",
            )
        else:
            self._status.setText(f"已还原 {result.moved} 个文件")
            QMessageBox.information(self, "还原完成", f"已还原 {result.moved} 个文件到原位置。")
        self._last_hid = None
        self.navigate.emit("home")

    # ----------------------------- reset ---------------------------------- #
    def _reset_to_config(self):
        self._scan_result = None
        self._set_busy(False)
        self._progress.setVisible(False)
        self._status.setVisible(False)
        self._show_empty_stage()

    # ----------------------------- busy / progress ------------------------ #
    def _busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def _set_busy(self, busy: bool):
        self._source.setDisabled(busy)
        self._scan_btn.setDisabled(busy)
        self._plan_btn.setDisabled(busy)
        self._mode_seg.setDisabled(busy)
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
        self._status.setText("发生错误，请重试")
        QMessageBox.critical(self, "错误", msg or "操作未完成，请重试。")

    # ----------------------------- theme ---------------------------------- #
    def _on_theme(self):
        self._recursive_toggle.update()

    def on_enter(self):
        # Keep the source box in sync with the latest chosen folder
        # (e.g. set from the dashboard hero before routing here).
        self._load_settings()

    def set_source(self, root: str):
        """P0 wiring: pre-fill the source box and persist it, then the
        AppShell triggers :meth:`_start_scan` to begin the run."""
        self._source.setText(root)
        settings_repo.set("last_source", root)
