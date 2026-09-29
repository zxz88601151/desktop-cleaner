"""History page (整理历史) — real timeline + one-click undo.

Lists every organize run from ``history_repo`` and lets the user undo a
*completed* run. Undo runs the exact 5-step reverse order from the old
``MainWindow``:

  history_repo.get -> operation_repo.list_by_history -> core.execute_undo
  -> operation_repo.update_status -> history_repo.update_status
  -> clean empty category dirs
"""
from __future__ import annotations

from datetime import datetime
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.organizer import OrganizeResult
from data import history_repo, operation_repo
from ui.icons import color, pixmap
from ui.state.worker import Worker
from ui.undo import ConfirmUndoDialog, run_undo

STATUS_LABELS = {
    "running": "进行中",
    "done": "已完成",
    "undone": "已撤销",
    "failed": "失败",
}

# V1.2-A: history now covers more than organizing, so the mode label / icon are
# looked up instead of hard-coded to "type vs date".
MODE_LABELS = {
    "type": "按类型整理",
    "date": "按日期整理",
    "empty_folders": "空文件夹清理",
}
MODE_ICONS = {
    "type": "folder",
    "date": "calendar",
    "empty_folders": "open_folder",
}
# What the row's count column means, per mode.
MODE_VERBS = {
    "type": "整理",
    "date": "整理",
    "empty_folders": "清理",
}


def _mode_label(mode: str) -> str:
    return MODE_LABELS.get(mode, mode)


def _mode_icon(mode: str) -> str:
    return MODE_ICONS.get(mode, "folder")


def _mode_verb(mode: str) -> str:
    return MODE_VERBS.get(mode, "整理")


def _relative_time(iso: str) -> str:
    """P2-4: human-friendly relative time from an ISO timestamp."""
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return iso[:10]
    sec = int((datetime.now() - dt).total_seconds())
    if sec < 60:
        return "刚刚"
    if sec < 3600:
        return f"{sec // 60} 分钟前"
    if sec < 86400:
        return f"{sec // 3600} 小时前"
    days = (datetime.now() - dt).days
    if days < 30:
        return f"{days} 天前"
    return dt.strftime("%Y-%m-%d")


class HistoryRow(QFrame):
    clicked = Signal(int)

    def __init__(self, rec: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("tl-row")
        self._hid = rec["id"]
        self._status = rec["status"]

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(12)

        icon = QLabel()
        icon.setObjectName("tl-ico")
        icon.setFixedSize(22, 22)
        icon.setPixmap(pixmap(_mode_icon(rec["mode"]), color("text_secondary"), 22))

        col = QVBoxLayout()
        col.setSpacing(2)
        title = QLabel(f"#{rec['id']}  ·  {_relative_time(rec['created_at'])}")
        title.setObjectName("tl-title")
        mode_text = _mode_label(rec["mode"])
        sub = QLabel(
            f"{mode_text}  ·  {_mode_verb(rec['mode'])} {rec['organized_files']} 个"
        )
        sub.setObjectName("tl-sub")
        src = QLabel(rec["source_path"])
        src.setObjectName("tl-sub")
        src.setWordWrap(True)
        col.addWidget(title)
        col.addWidget(sub)
        col.addWidget(src)

        tag = QLabel(STATUS_LABELS.get(rec["status"], rec["status"]))
        tag.setObjectName("tl-tag")
        tag.setProperty("state", rec["status"])

        lay.addWidget(icon)
        lay.addLayout(col, 1)
        lay.addWidget(tag)

    def mousePressEvent(self, _):
        self.clicked.emit(self._hid)

    def set_selected(self, selected: bool):
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    @property
    def hid(self) -> int:
        return self._hid

    @property
    def status(self) -> str:
        return self._status


class HistoryPage(QWidget):
    navigate = Signal(str)
    finished = Signal()  # emitted after a successful undo

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._worker: Worker | None = None
        self._rows: list[HistoryRow] = []
        self._selected_hid: int | None = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        self._title = QLabel("整理历史")
        self._title.setObjectName("page-title")
        self._sub = QLabel("每一次整理都记录在案，可随时一键撤销还原。")
        self._sub.setObjectName("page-sub")
        root.addWidget(self._title)
        root.addWidget(self._sub)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list = QWidget()
        self._list_lay = QVBoxLayout(self._list)
        self._list_lay.setContentsMargins(0, 0, 0, 0)
        self._list_lay.setSpacing(12)
        self._scroll.setWidget(self._list)
        root.addWidget(self._scroll, 1)

        self._empty = QLabel("还没有整理记录。去「整理」整理一次吧。")
        self._empty.setObjectName("page-sub")
        self._empty.setWordWrap(True)

        bar = QHBoxLayout()
        bar.setSpacing(12)
        self._undo_btn = QPushButton("撤销选中整理")
        self._undo_btn.setObjectName("undo-cta")
        self._undo_btn.setMinimumHeight(42)
        self._undo_btn.setEnabled(False)
        self._undo_btn.clicked.connect(self._start_undo)
        home = QPushButton("返回整理")
        home.setObjectName("ghost")
        home.clicked.connect(lambda: self.navigate.emit("organize"))
        bar.addWidget(self._undo_btn)
        bar.addWidget(home)
        bar.addStretch(1)
        root.addLayout(bar)

    # ----------------------------- load ----------------------------------- #
    def on_enter(self):
        self.refresh()

    def refresh(self):
        self._clear()
        rows = history_repo.list_all(100)
        if not rows:
            self._list_lay.addWidget(self._empty)
            self._list_lay.addStretch(1)
            self._undo_btn.setEnabled(False)
            return
        for rec in rows:
            row = HistoryRow(rec)
            row.clicked.connect(self._on_row_clicked)
            self._rows.append(row)
            self._list_lay.addWidget(row)
        self._list_lay.addStretch(1)
        # auto-select the most recent done run
        for row in self._rows:
            if row.status == "done":
                self._on_row_clicked(row.hid)
                break

    def _clear(self):
        self._rows = []
        self._selected_hid = None
        while self._list_lay.count():
            item = self._list_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

    def _on_row_clicked(self, hid: int):
        self._selected_hid = hid
        sel_status = None
        for row in self._rows:
            on = row.hid == hid
            row.set_selected(on)
            if on:
                sel_status = row.status
        self._undo_btn.setEnabled(sel_status == "done")

    # ----------------------------- undo ----------------------------------- #
    def _start_undo(self):
        self.request_undo(self._selected_hid)

    def request_undo(self, hid: int | None):
        """统一撤销入口：确认 -> Worker 跑 5 步 -> 刷新。

        完成页 / 首页的一键还原也通过此方法触发，避免重复代码。
        """
        if hid is None or self._busy():
            return
        rec = history_repo.get(hid)
        if rec is None or rec["status"] != "done":
            return
        ops = operation_repo.list_by_history(hid)
        dlg = ConfirmUndoDialog(hid, len(ops), rec["source_path"], self)
        if dlg.exec() != 1:  # QDialog.Accepted
            return
        self._set_busy(True)
        self._worker = Worker(lambda p, l: run_undo(hid, p, l))
        self._worker.progress.connect(lambda *_: None)
        self._worker.log.connect(lambda *_: None)
        self._worker.finished.connect(self._on_undo_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_undo_done(self, payload: dict):
        result: OrganizeResult = payload["result"]
        self._set_busy(False)
        self.refresh()
        self.finished.emit()
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(
            self, "撤销完成", f"已还原 {result.moved} 个文件到原位置。"
        )

    def _on_error(self, msg: str):
        self._set_busy(False)
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.critical(self, "错误", msg or "操作未完成，请重试。")

    def _busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def _set_busy(self, busy: bool):
        self._undo_btn.setDisabled(busy)
        for row in self._rows:
            row.setDisabled(busy)
