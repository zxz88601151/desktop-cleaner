"""Application logger (file-based, non-blocking to the UI)."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

# desktop_cleaner.log rotates at 1 MB, keeping 2 previous files, so the log can
# never grow without bound inside %APPDATA%.
_MAX_BYTES = 1 * 1024 * 1024
_BACKUP_COUNT = 2

_file_handler: logging.Handler | None = None


def _shared_file_handler() -> logging.Handler | None:
    """One rotating handler shared by every named logger (or ``None``).

    The old shape attached a plain ``FileHandler`` per logger *name*, i.e. up to
    8 append-mode handles on the same file with no cross-handler lock (lines can
    interleave on Windows) and no size bound. Sharing a single
    ``RotatingFileHandler`` fixes both: its lock serialises writes, and
    rotation is only ever attempted by the one handle that owns the file.
    """
    global _file_handler
    if _file_handler is not None:
        return _file_handler
    try:
        from data.database import DB_DIR

        log_path = DB_DIR / "desktop_cleaner.log"
        fh = RotatingFileHandler(
            log_path,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        # Structured yet human-readable: time / level / module / message.
        # Per-failure operation/source/target/error fields are embedded in the
        # message by the callers (see organizer.move_items), so the log stays
        # single-line machine-parseable AND readable.
        fh.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s %(message)s")
        )
        _file_handler = fh
    except Exception:
        # Logging must never break the app; the caller falls back to stderr.
        _file_handler = None
    return _file_handler


def get_logger(name: str = "desktop_cleaner") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = _shared_file_handler()
    if handler is not None:
        logger.addHandler(handler)
    else:
        logging.basicConfig(level=logging.INFO)
    return logger
