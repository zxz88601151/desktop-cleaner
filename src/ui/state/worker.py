"""Reusable background task runner (UI Migration Audit, Phase 1+).

Moved out of the old ``MainWindow`` god-object so any page can run a
blocking business task off the UI thread. The task callable receives
``(progress_cb, log_cb)`` and may return any object forwarded through
:attr:`finished`.

Business layer stays frozen: this only wraps ``core.*`` / ``data.*`` calls
chosen by the calling page.
"""
from __future__ import annotations

import traceback
from PySide6.QtCore import QThread, Signal

from utils.errors import friendly_message
from utils.logger import get_logger

_log = get_logger("worker")


class Worker(QThread):
    """Runs a blocking task off the UI thread."""

    progress = Signal(int, int, str)
    log = Signal(str)
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def _p(self, cur: int, total: int, msg: str):
        self.progress.emit(cur, total, msg)

    def _l(self, msg: str):
        self.log.emit(msg)

    def run(self):
        try:
            result = self.fn(self._p, self._l)
            self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001 - report to UI
            # P1-6: the full traceback goes to the log file (diagnostics);
            # the UI receives only a calm, actionable, non-technical message.
            _log.error("Worker task failed:\n%s", traceback.format_exc())
            self.error.emit(friendly_message(exc))
