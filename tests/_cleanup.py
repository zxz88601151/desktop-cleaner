"""Sandbox cleanup helper for the standalone UI test scripts.

PHASE PRIVATE LIBRARY — UI TEST SAFETY REMEDIATION-1 (Stage 1).

Why this exists
---------------
The six standalone scripts (`test_appshell.py`, `test_dashboard.py`,
`test_theme.py`, `test_preview.py`, `test_first_launch.py`,
`test_phase5_e2e.py`) used to end with::

    finally:
        shutil.rmtree(_TMP_HOME, ignore_errors=True)

On Windows that cleanup silently did nothing, because **two process-lifetime
handles** stayed open on files inside the sandbox (both reproduced with
throw-away probes during the audit):

1. ``sqlite3.Connection`` — every ``src/data/*`` helper uses
   ``with get_connection() as conn:``, which is a *transaction* context manager
   (commit/rollback) and does **not** close the connection. The connection sits
   in a reference cycle, so refcounting never frees it; only a ``gc`` pass does.
   Symptom: ``PermissionError [WinError 32]`` on ``data/desktop_cleaner.db``
   (plus ``-wal`` / ``-shm``).
2. ``logging.FileHandler`` — ``utils/logger.py`` caches a handler on a
   *process-global* logger (``Logger.manager.loggerDict``) and never closes it.
   ``gc.collect()`` does **not** help here. Symptom: ``WinError 32`` on
   ``data/desktop_cleaner.log``.

``ignore_errors=True`` then swallowed both failures, so ~237 stale directories
accumulated in ``%TEMP%``.

What this module does
---------------------
``cleanup_home(path)`` releases only the resources that provably belong to the
given sandbox, then deletes it — and **raises** if it cannot:

* log handlers are closed only when ``handler.baseFilename`` resolves *inside*
  the sandbox (deliberately NOT ``logging.shutdown()``, which would tear down
  handlers belonging to other tests sharing the process);
* SQLite connections are closed explicitly, with ownership proven via the public
  ``PRAGMA database_list`` path check;
* ``gc.collect()`` is kept as an **evidence-backed test-side mitigation** for
  connections the product code leaves in a reference cycle — it is NOT a
  product-layer fix (see the Stage 2 note below);
* ``shutil.rmtree`` runs **without** ``ignore_errors``, with a bounded retry,
  and the final exception is preserved and re-raised. When a descendant path
  exceeds ``MAX_PATH`` (``t06``'s deep-path scenario, which now lives *inside*
  the sandbox) plain ``shutil.rmtree`` raises ``WinError 145``; removal is then
  retried through the ``\\\\?\\`` extended-length prefix.

Safety: every path touched is checked to be inside ``root``. Nothing outside the
sandbox is ever read, written or deleted.

Out of scope (Stage 2 / needs separate authorization)
----------------------------------------------------
The root causes live in product code (``src/data/*`` never closing connections;
``src/utils/logger.py`` holding a process-lifetime handler). Fixing those is a
product change and was explicitly deferred. This helper is a test-side
mitigation only.
"""
from __future__ import annotations

import gc
import logging
import os
import shutil
import sqlite3
import time
from pathlib import Path

__all__ = ["cleanup_home", "is_inside"]

# Bounded retry: 5 attempts, 100 ms apart. Windows can keep a directory handle
# alive for a few milliseconds after the last close().
_RETRIES = 5
_RETRY_DELAY_S = 0.1


def is_inside(path, root) -> bool:
    """True when ``path`` resolves to ``root`` or something below it."""
    try:
        return Path(path).resolve().is_relative_to(Path(root).resolve())
    except (OSError, ValueError):
        return False


def _close_sandbox_log_handlers(root: Path) -> int:
    """Close + detach only the FileHandlers that write inside ``root``.

    Ownership test is the handler's own ``baseFilename``. Handlers pointing
    anywhere else (including a real application log) are left untouched.
    """
    closed = 0
    loggers = [logging.getLogger()]
    loggers += [logging.getLogger(name) for name in list(logging.Logger.manager.loggerDict)]

    for logger in loggers:
        for handler in list(logger.handlers):
            base = getattr(handler, "baseFilename", None)
            if not base or not is_inside(base, root):
                continue
            try:
                handler.flush()
            except Exception:  # noqa: BLE001 - best effort
                pass
            try:
                handler.close()
            except Exception:  # noqa: BLE001 - best effort
                pass
            logger.removeHandler(handler)
            closed += 1
    return closed


def _close_sandbox_sqlite(root: Path) -> int:
    """Explicitly close sqlite3 connections whose database file is inside ``root``.

    Ownership is proven with ``PRAGMA database_list`` (public API) rather than
    guessing. Best-effort: the caller still retries and finally raises, so a
    failure here cannot turn into a silent pass.
    """
    closed = 0
    for obj in gc.get_objects():
        if not isinstance(obj, sqlite3.Connection):
            continue
        try:
            rows = obj.execute("PRAGMA database_list").fetchall()
        except Exception:  # noqa: BLE001 - already closed / not queryable
            continue
        if any(row[2] and is_inside(row[2], root) for row in rows):
            try:
                obj.close()
                closed += 1
            except Exception:  # noqa: BLE001 - best effort
                pass
    return closed


def _extended(path) -> str:
    """Absolute path in Windows extended-length (``\\\\?\\``) form.

    Paths longer than ``MAX_PATH`` cannot be opened by ``os.scandir`` /
    ``os.rmdir``, which is exactly what ``t06``'s deep-path scenario produces.
    """
    text = os.fspath(path)
    if os.name != "nt" or text.startswith("\\\\?\\"):
        return text
    return "\\\\?\\" + os.path.abspath(text).replace("/", "\\")


def _rmtree_extended(path) -> None:
    """Recursive delete that also works beyond ``MAX_PATH``."""
    target = _extended(path)
    if not os.path.lexists(target):
        return
    if os.path.isdir(target) and not os.path.islink(target):
        with os.scandir(target) as entries:
            for entry in entries:
                _rmtree_extended(entry.path)
        os.rmdir(target)
    else:
        os.unlink(target)


def _remove_tree(root: Path) -> None:
    """Delete ``root``, falling back to the long-path-aware walker."""
    try:
        shutil.rmtree(root)
        return
    except FileNotFoundError:
        return
    except OSError:
        pass  # most likely a descendant beyond MAX_PATH; retry extended
    _rmtree_extended(root)


def cleanup_home(root) -> None:
    """Release sandbox-owned resources, then delete the sandbox.

    Raises the final ``OSError`` (chained) if the directory still cannot be
    removed — cleanup failures must stay visible instead of being swallowed.

    A already-absent directory counts as success, so calling this twice (e.g.
    once from ``finally`` and once from an outer guard) is harmless.
    """
    root = Path(root)

    _close_sandbox_log_handlers(root)
    _close_sandbox_sqlite(root)
    # Evidence-backed mitigation for the cyclic sqlite3.Connection objects that
    # product code leaves behind (see module docstring). Not a product fix.
    gc.collect()

    last_error: OSError | None = None
    for _ in range(_RETRIES):
        try:
            _remove_tree(root)
            return
        except FileNotFoundError:
            return
        except OSError as exc:
            last_error = exc
            time.sleep(_RETRY_DELAY_S)

    raise RuntimeError(
        f"cleanup_home failed to remove sandbox {root!s}: {last_error}"
    ) from last_error
