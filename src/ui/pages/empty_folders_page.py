"""Empty-folder cleanup page (V1.2-A, feature 1).

Flow (mirrors the organize page's discipline):
    选源 -> find_empty_folders (真实扫描, 只读) -> 逐项勾选预览
         -> 二次确认 -> cleanup (移入隔离区, 复用 core.organizer.move_items)
         -> 记录 history + operations -> 完成态 (可一键还原)

Safety: scanning is read-only; nothing is deleted (folders are MOVED into a
quarantine folder inside the same root); the run is recorded and undoable; a
folder that gained content after the scan is skipped, not removed.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
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

from core import cleanup, find_empty_folders, plan_cleanup, total_nested
from core.empty_folders import QUARANTINE_DIRNAME, EmptyFolder
from data import history_repo, operation_repo, settings_repo
from ui.icons import color, pixmap
from ui.state.worker import Worker
from ui.theme_manager import ThemeManager
from ui.undo import ConfirmUndoDialog, run_undo
from ui.widgets.controls import ToggleSwitch

MODE = "empty_folders"


class EmptyFoldersPage(QWidget):
    navigate = Signal(str)
    finished = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._worker: Worker | None = None
        self._root: str | None = None
        self._recursive = True
        self._folders: list[EmptyFolder] = []
        self._rows: list[tuple[QCheckBox, EmptyFolder]] = []
        self._last_hid: int | None = None
        self._build()
        ThemeManager.instance().on_changed(self._on_theme)

    # ----------------------------- build --------------------------------- #
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        title = QLabel("空文件夹清理")
        title.setObjectName("page-title")
        sub = QLabel("找出没有内容的空文件夹 — 只移动、不删除，可随时还原")
        sub.setObjectName("page-sub")
        root.addWidget(title)
        root.addWidget(sub)

        card = QFrame()
        card.setObjectName("step-card")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(22, 22, 22, 22)
        cv.setSpacing(14)

        fl = QLabel("清理文件夹")
        fl.setObjectName("field-label")
        cv.addWidget(fl)

        src_row = QHBoxLayout()
        src_row.setSpacing(10)
        self._source = QLineEdit()
        self._source.setPlaceholderText("点击右侧按钮选择要清理的文件夹，例如：桌面 / 下载")
        browse = QPushButton("选择文件夹")
        browse.setObjectName("secondary")
        browse.clicked.connect(self._browse)
        src_row.addWidget(self._source, 1)
        src_row.addWidget(browse)
        cv.addLayout(src_row)

        opt_row = QHBoxLayout()
        opt_row.setSpacing(14)
        self._recursive_toggle = ToggleSwitch(True)
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

        self._build_preview_stage()
        self._build_done_stage()
        self._show_empty_stage()
        self._load_settings()

    def _build_preview_stage(self):
        self._preview = QWidget()
        pv = QVBoxLayout(self._preview)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(10)

        bar = QHBoxLayout()
        bar.setSpacing(10)
        self._summary = QLabel()
        self._summary.setObjectName("summary-line")
        self._select_all = QPushButton("全选 / 全不选")
        self._select_all.setObjectName("ghost")
        self._select_all.clicked.connect(self._toggle_all)
        bar.addWidget(self._summary, 1)
        bar.addWidget(self._select_all)
        pv.addLayout(bar)

        self._list = QFrame()
        self._list.setObjectName("panel")
        self._list_lay = QVBoxLayout(self._list)
        self._list_lay.setContentsMargins(8, 8, 8, 8)
        self._list_lay.setSpacing(6)
        pv.addWidget(self._list, 1)

        self._clean_btn = QPushButton("清理选中")
        self._clean_btn.setObjectName("primary")
        self._clean_btn.setMinimumHeight(44)
        self._clean_btn.clicked.connect(self._start_cleanup)
        pv.addWidget(self._clean_btn)

    def _build_done_stage(self):
        self._done = QWidget()
        dv = QVBoxLayout(self._done)
        dv.setContentsMargins(0, 12, 0, 0)
        dv.setSpacing(12)
        dv.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ico = QLabel()
        ico.setFixedSize(46, 46)
        ico.setPixmap(pixmap("check", color("success"), 46))
        ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._done_title = QLabel("清理完成")
        self._done_title.setObjectName("result-title")
        self._done_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._done_sub = QLabel()
        self._done_sub.setObjectName("result-sub")
        self._done_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._done_sub.setWordWrap(True)
        dv.addWidget(ico)
        dv.addWidget(self._done_title)
        dv.addWidget(self._done_sub)
        dv.addSpacing(10)

        row = QHBoxLayout()
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.setSpacing(12)
        undo_btn = QPushButton("一键还原本次清理")
        undo_btn.setObjectName("undo-cta")
        undo_btn.setMinimumHeight(44)
        undo_btn.clicked.connect(self._undo_this)
        hist_btn = QPushButton("查看历史")
        hist_btn.setObjectName("ghost")
        hist_btn.clicked.connect(lambda: self.navigate.emit("history"))
        again = QPushButton("再清理一次")
        again.setObjectName("tertiary")
        again.clicked.connect(self._reset_to_config)
        row.addWidget(undo_btn)
        row.addWidget(hist_btn)
        row.addWidget(again)
        dv.addLayout(row)

    # ----------------------------- stage helpers -------------------------- #
    def _show_empty_stage(self):
        self._clear_stage()
        hint = QLabel(
            "选择文件夹后点击「开始扫描」，我们会列出空文件夹供你确认，"
            "确认后才移动（移入隔离区，不删除、可还原）。"
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

    def _set_stage(self, widget: QWidget):
        self._clear_stage()
        self._stage_lay.addWidget(widget, 1)
        self._stage_lay.addStretch(1)

    # ----------------------------- settings ------------------------------- #
    def _load_settings(self):
        last = settings_repo.get("last_source")
        if last and Path(last).is_dir():
            self._source.setText(last)
        else:
            desktop = str(Path.home() / "Desktop")
            if Path(desktop).is_dir():
                self._source.setText(desktop)

    def _on_recursive(self, on: bool):
        self._recursive = on

    def _browse(self):
        start = self._source.text() or str(Path.home())
        d = QFileDialog.getExistingDirectory(self, "选择要清理的文件夹", start)
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
        self._progress.setRange(0, 0)
        self._status.setVisible(True)
        self._status.setText(f"正在扫描空文件夹：{root} …")
        self._worker = Worker(lambda p, l: self._task_scan(root, self._recursive, p, l))
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_scan_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    @staticmethod
    def _task_scan(root, recursive, p, l):
        folders = find_empty_folders(Path(root), recursive=recursive)
        l(f"发现 {len(folders)} 个空文件夹")
        return folders

    def _on_scan_done(self, folders: list[EmptyFolder]):
        self._set_busy(False)
        self._progress.setVisible(False)
        self._folders = folders
        if not folders:
            self._status.setText("扫描完成：没有发现空文件夹")
            self._show_empty_stage()
            return
        self._status.setText(
            f"扫描完成：{len(folders)} 个空文件夹（共 {total_nested(folders)} 个目录）"
        )
        self._render_list(folders)
        self._set_stage(self._preview)

    def _render_list(self, folders: list[EmptyFolder]):
        while self._list_lay.count():
            item = self._list_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        self._rows = []
        for f in folders:
            row = QFrame()
            row.setObjectName("cat-row")
            rv = QHBoxLayout(row)
            rv.setContentsMargins(14, 10, 14, 10)
            rv.setSpacing(10)
            cb = QCheckBox()
            cb.setChecked(True)
            cb.stateChanged.connect(self._update_action)
            col = QVBoxLayout()
            col.setSpacing(2)
            nm = QLabel(f.path.name)
            nm.setObjectName("tl-title")
            detail = f"{f.path}"
            if f.nested:
                detail += f"  ·  含 {f.nested} 个子文件夹"
            if f.mtime:
                try:
                    detail += "  ·  最后修改 " + datetime.fromtimestamp(
                        f.mtime
                    ).strftime("%Y-%m-%d")
                except (ValueError, OSError):
                    pass
            ds = QLabel(detail)
            ds.setObjectName("tl-sub")
            ds.setWordWrap(True)
            col.addWidget(nm)
            col.addWidget(ds)
            rv.addWidget(cb)
            rv.addLayout(col, 1)
            self._rows.append((cb, f))
            self._list_lay.addWidget(row)
        self._update_action()

    def _selected(self) -> list[EmptyFolder]:
        return [f for cb, f in self._rows if cb.isChecked()]

    def _toggle_all(self):
        target = not all(cb.isChecked() for cb, _ in self._rows)
        for cb, _ in self._rows:
            cb.setChecked(target)
        self._update_action()

    def _update_action(self):
        n = len(self._selected())
        self._clean_btn.setEnabled(n > 0)
        self._clean_btn.setText(f"清理选中的 {n} 个空文件夹" if n else "清理选中")
        self._summary.setText(
            f"共发现 {len(self._folders)} 个空文件夹，已选择 {n} 个"
        )

    # ----------------------------- execute -------------------------------- #
    def _start_cleanup(self):
        if self._root is None or self._busy():
            return
        selected = self._selected()
        if not selected:
            return
        total = total_nested(selected)
        preview = "\n".join(f"• {f.path}" for f in selected[:15])
        more = f"\n… 其余 {len(selected) - 15} 个" if len(selected) > 15 else ""
        ans = QMessageBox.question(
            self,
            "确认清理空文件夹",
            f"将把 {len(selected)} 个空文件夹（共 {total} 个目录）移入隔离区：\n\n"
            f"{preview}{more}\n\n"
            f"移动到：{Path(self._root) / QUARANTINE_DIRNAME}\n"
            "不会删除任何文件，清理后可一键还原。是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        self._set_busy(True)
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        self._status.setVisible(True)
        self._status.setText("正在清理空文件夹…")
        self._worker = Worker(
            lambda p, l: self._task_cleanup(self._root, selected, p, l)
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_cleanup_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    @staticmethod
    def _task_cleanup(root, folders, p, l):
        # Same strict ordering as organize: history -> pending ops -> move -> settle
        items = plan_cleanup(Path(root), folders)
        hid = history_repo.create(root, MODE, len(items))
        l(f"已创建清理记录 #{hid}")
        operation_repo.bulk_insert_pending(hid, items)
        res = cleanup(Path(root), folders, on_progress=p)
        result = res.result
        moved = {str(i.target) for i in (result.items if result else [])}
        failed = {str(i.target) for i in (result.failed_items if result else [])}
        operation_repo.update_statuses_by_target(hid, moved, failed)
        history_repo.update_status(
            hid, "done", res.moved, res.failed + len(res.stale)
        )
        return {"hid": hid, "res": res}

    def _on_cleanup_done(self, payload: dict):
        res = payload["res"]
        self._last_hid = payload["hid"]
        self._set_busy(False)
        self._progress.setVisible(False)
        msg = f"已清理 {res.moved} 个空文件夹（移入隔离区）。"
        if res.stale:
            msg += f"\n{len(res.stale)} 个已跳过：扫描后内容发生变化。"
        if res.failed:
            msg += f"\n{res.failed} 个失败。"
        self._status.setText(
            f"清理完成：移动 {res.moved} 个，跳过 {len(res.stale)} 个，失败 {res.failed} 个"
        )
        self._done_sub.setText(msg + "\n如需恢复，可在「整理历史」中撤销。")
        self._set_stage(self._done)
        self.finished.emit()

    # ----------------------------- undo ----------------------------------- #
    def _undo_this(self):
        if self._last_hid is None or self._busy():
            return
        rec = history_repo.get(self._last_hid)
        if rec is None or rec["status"] != "done":
            return
        ops = operation_repo.list_by_history(self._last_hid)
        dlg = ConfirmUndoDialog(self._last_hid, len(ops), rec["source_path"], self)
        if dlg.exec() != 1:
            return
        self._set_busy(True)
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        self._status.setVisible(True)
        self._status.setText("正在还原…")
        self._worker = Worker(lambda p, l: run_undo(self._last_hid, p, l))
        self._worker.progress.connect(self._on_progress)
        self._worker.log.connect(self._on_log)
        self._worker.finished.connect(self._on_undo_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_undo_done(self, payload: dict):
        result = payload["result"]
        failed = payload.get("failed_files") or []
        self._set_busy(False)
        self._progress.setVisible(False)
        if failed:
            QMessageBox.warning(
                self, "还原未完成",
                f"已还原 {result.moved} 个，{len(failed)} 个失败。",
            )
        else:
            QMessageBox.information(
                self, "还原完成", f"已还原 {result.moved} 个空文件夹到原位置。"
            )
        self._last_hid = None
        self._reset_to_config()

    # ----------------------------- reset / busy --------------------------- #
    def _reset_to_config(self):
        self._folders = []
        self._rows = []
        self._set_busy(False)
        self._progress.setVisible(False)
        self._status.setVisible(False)
        self._show_empty_stage()

    def _busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def _set_busy(self, busy: bool):
        self._source.setDisabled(busy)
        self._scan_btn.setDisabled(busy)
        self._recursive_toggle.setDisabled(busy)
        self._clean_btn.setDisabled(busy or not self._selected())

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
        self._status.setText("操作失败")
        QMessageBox.critical(self, "错误", msg or "操作未完成，请重试。")

    def _on_theme(self):
        self._recursive_toggle.update()

    def on_enter(self):
        self._load_settings()
