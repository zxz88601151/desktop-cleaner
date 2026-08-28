"""Update manager — Qt glue.

Runs the (pure) network fetch inside a QThread so it never blocks the UI or startup.
Throttles automatic checks to once per 24h via the existing settings store. Emits:
- `update_available(manifest)` when a newer version is found (and not force-skipped)
- `no_update()`            when up to date / check skipped by throttle / check failed

Failure is always silent (server down / offline / malformed) — the app must open
normally regardless. The manager never downloads or replaces the EXE (Option B).
"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QObject, QThread, Signal

from data import settings_repo

from .checker import fetch_manifest
from .constants import UPDATE_CHECK_INTERVAL_HOURS
from .decision import LEVEL_NONE, evaluate

_LAST_CHECK_KEY = "last_update_check"


class _CheckWorker(QThread):
    """Background fetcher. Emits the manifest dict or None."""

    got = Signal(object)

    def run(self):  # pragma: no cover - exercised by the event loop in tests
        self.got.emit(fetch_manifest())


class UpdateManager(QObject):
    update_available = Signal(dict)
    no_update = Signal()

    def __init__(self, current_version: str, parent: QObject | None = None):
        super().__init__(parent)
        self._current = current_version
        self._worker: _CheckWorker | None = None

    # -- throttle ---------------------------------------------------------- #
    def _should_check(self) -> bool:
        last = settings_repo.get(_LAST_CHECK_KEY)
        if not last:
            return True
        try:
            age_h = (datetime.now() - datetime.fromisoformat(last)).total_seconds() / 3600.0
            return age_h >= UPDATE_CHECK_INTERVAL_HOURS
        except Exception:
            return True

    def _mark_checked(self):
        settings_repo.set(_LAST_CHECK_KEY, datetime.now().isoformat())

    # -- entry points ----------------------------------------------------- #
    def start_check(self, force: bool = False):
        """Kick off a background update check.

        Non-`force` checks are throttled to once per 24h. The fetch runs on a worker
        thread; results arrive via `_on_result` on the Qt thread.
        """
        if not force and not self._should_check():
            self.no_update.emit()
            return
        self._mark_checked()
        self._worker = _CheckWorker()
        self._worker.got.connect(self._on_result)
        self._worker.start()

    def _on_result(self, manifest):
        if not manifest or evaluate(self._current, manifest) == LEVEL_NONE:
            self.no_update.emit()
        else:
            self.update_available.emit(manifest)
