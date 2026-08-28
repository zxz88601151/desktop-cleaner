"""一键还原（撤销整理）共享任务 + 安全确认弹窗。

把「完成页 / 首页 / 历史页」三处触发撤销的逻辑收敛到同一套：
  - ``run_undo``：严格 5 步反向顺序（与旧 MainWindow 一致）
  - ``ConfirmUndoDialog``：轻量二次确认（撤销会移动文件，需确认）

业务层 ``core/`` 保持冻结，本模块只编排已有 API。
"""
from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)

from core import execute_undo
from data import history_repo, operation_repo
from utils.logger import get_logger

_log = get_logger("undo")


def run_undo(hid: int, on_progress=None, on_log=None) -> dict:
    """撤销一次已完成整理，严格 5 步反向顺序：

        history_repo.get -> operation_repo.list_by_history
        -> core.execute_undo -> operation_repo.apply_undo_result (P0-2)
        -> history_repo.update_status(undone, 仅全成功) -> 清空空分类目录
    """
    hist = history_repo.get(hid)
    if hist is None or hist["status"] != "done":
        raise ValueError("该记录不可撤销")
    ops = operation_repo.list_by_history(hid)
    _log.info("UNDO START hid=%s files=%d", hid, len(ops))
    if on_log:
        on_log(f"共需还原 {len(ops)} 个文件")
    result = execute_undo(ops, on_progress=on_progress)
    # P0-2: only successfully-restored ops become 'undone'; failures keep
    # 'moved' and are returned so the UI can surface them. History is marked
    # 'undone' only when the whole undo succeeded (no failures).
    failed_files = operation_repo.apply_undo_result(hid, result)
    if not failed_files:
        history_repo.update_status(hid, "undone")
        _remove_empty_category_dirs(Path(hist["source_path"]))
        _log.info("UNDO DONE hid=%s restored=%d", hid, result.moved)
    else:
        _log.warning(
            "UNDO PARTIAL hid=%s restored=%d failed=%d",
            hid, result.moved, result.failed,
        )
    return {"hid": hid, "result": result, "failed_files": failed_files}


def _remove_empty_category_dirs(root: Path):
    """撤销后清理变成空的分类 / 日期目录。"""
    try:
        from core.rules import CATEGORY_NAMES, is_date_dir

        names = set(CATEGORY_NAMES.values())
        for child in root.iterdir():
            if not child.is_dir():
                continue
            if child.name in names or is_date_dir(child.name):
                if not any(child.iterdir()):
                    shutil.rmtree(child, ignore_errors=True)
    except Exception:  # noqa: BLE001 - 尽力清理，失败不影响主流程
        pass


class ConfirmUndoDialog(QDialog):
    """撤销前的轻量确认：告知将还原 N 个文件及源路径。"""

    def __init__(self, hid: int, count: int, root: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("确认还原")
        self.setMinimumWidth(420)
        self.setModal(True)
        self.setObjectName("confirm-undo")

        # Reuse existing history data (read-only) for the organize timestamp.
        created = ""
        hist = history_repo.get(hid)
        if hist and hist.get("created_at"):
            try:
                from datetime import datetime

                created = datetime.fromisoformat(hist["created_at"]).strftime(
                    "%Y-%m-%d %H:%M"
                )
            except Exception:  # noqa: BLE001 - fall back to raw value
                created = str(hist["created_at"])

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 20)
        lay.setSpacing(14)

        icon = QLabel("♻️")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size:34px;")
        lay.addWidget(icon)

        title = QLabel("撤销本次整理？")
        title.setObjectName("dialog-title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        time_line = (
            f"整理时间：{created}\n\n" if created else ""
        )
        body = QLabel(
            f"将把 <b>{count}</b> 个文件还原回原文件夹：\n"
            f"<span style='color:{_accent()}'>{root}</span>\n\n"
            f"{time_line}"
            "文件只移动、不删除。还原后可在「整理历史」中再次整理。\n\n"
            "提示：若原位置已被改动或发生冲突，部分文件可能无法恢复。"
        )
        body.setObjectName("dialog-body")
        body.setWordWrap(True)
        lay.addWidget(body)

        box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        ok = box.button(QDialogButtonBox.StandardButton.Ok)
        ok.setText("还原")
        ok.setObjectName("undo-cta")
        cancel = box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel.setText("取消")
        cancel.setObjectName("ghost")
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        lay.addWidget(box)


def _accent() -> str:
    from ui.theme.themes import THEMES
    from ui.theme_manager import ThemeManager

    return THEMES.get(ThemeManager.instance().theme, THEMES["light"])["accent"]
