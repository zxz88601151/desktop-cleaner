"""Application logger (file-based, non-blocking to the UI)."""
from __future__ import annotations

import logging
from pathlib import Path


def get_logger(name: str = "desktop_cleaner") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    try:
        from data.database import DB_DIR

        log_path = DB_DIR / "desktop_cleaner.log"
        fh = logging.FileHandler(log_path, encoding="utf-8")
        # Structured yet human-readable: time / level / module / message.
        # Per-failure operation/source/target/error fields are embedded in the
        # message by the callers (see organizer.move_items), so the log stays
        # single-line machine-parseable AND readable.
        fh.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s %(message)s")
        )
        logger.addHandler(fh)
    except Exception:
        # Logging must never break the app; fall back to stderr only.
        logging.basicConfig(level=logging.INFO)
    return logger
