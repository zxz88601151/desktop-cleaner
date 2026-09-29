"""Update manager — Qt glue.

Runs the (pure) network fetch inside a QThread so it never blocks the UI or startup.
Throttles automatic checks to once per 24h via the existing settings store. Emits:
- `update_available(manifest)` when a newer version is found
- `no_update()`               when the check genuinely succeeded and is up to date,
                              or when the check was skipped by the throttle
- `check_failed()`            when the fetch/parse FAILED (offline / timeout / TLS /
                              malformed). Kept separate from `no_update` so the UI
                              can never report a network failure as "已是最新".

Failure is always silent for *background* checks (the app must open normally
regardless), but it is now distinguishable from "up to date". The 24h throttle is
only consumed by a *successful* fetch, so a transient failure is retried on the
next launch instead of being suppressed for a day. The manager never downloads or
replaces the EXE (Option B).
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
    check_failed = Signal()

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

        NOTE: the throttle is *not* consumed here — only a successful fetch marks
        the window (see :meth:`_on_result`), so a failed check can retry next launch.
        """
        if not force and not self._should_check():
            # Throttled: nothing to report, and nothing failed.
            self.no_update.emit()
            return
        self._worker = _CheckWorker()
        self._worker.got.connect(self._on_result)
        # Free the thread object once it finishes (avoids accumulating QThreads).
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _on_result(self, manifest):
        if not manifest:
            # Fetch or parse failed (offline / timeout / TLS / malformed JSON).
            # This is NOT "up to date" — report it on its own signal so the UI
            # never shows a false "已是最新", and leave the throttle window open
            # so the next launch retries.
            self.check_failed.emit()
            return
        # Only a successful fetch counts against the 24h throttle.
        self._mark_checked()
        if evaluate(self._current, manifest) == LEVEL_NONE:
            self.no_update.emit()
        else:
            self.update_available.emit(manifest)
