"""SQLite connection management and schema migrations."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# Resolve the data directory:
# - env DESKTOP_CLEANER_HOME (if set): portable / test override
# - frozen (PyInstaller, both one-file and one-folder): %APPDATA%/DesktopCleaner
#   so the SQLite DB survives restarts even in one-file mode.
# - source run: <project root>/data   (src/data/database.py -> parents[2])
def _app_base() -> Path:
    import os

    env = os.environ.get("DESKTOP_CLEANER_HOME")
    if env:
        return Path(env)
    if getattr(sys, "frozen", False):
        appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
        return Path(appdata) / "DesktopCleaner"
    return Path(__file__).resolve().parents[2]


DB_DIR = _app_base() / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "desktop_cleaner.db"


def data_dir() -> Path:
    """The application's own data directory (holds ``desktop_cleaner.db``).

    Used by the scanner as a safety guard: the user must never be allowed to
    organize this folder, or the database file itself would be moved.
    """
    return DB_DIR

_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path     TEXT NOT NULL,
    mode            TEXT NOT NULL,
    total_files     INTEGER DEFAULT 0,
    organized_files INTEGER DEFAULT 0,
    skipped_files   INTEGER DEFAULT 0,
    status          TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS operations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    history_id   INTEGER NOT NULL,
    source_path  TEXT NOT NULL,
    target_path  TEXT NOT NULL,
    file_name    TEXT NOT NULL,
    category     TEXT NOT NULL,
    status       TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    FOREIGN KEY (history_id) REFERENCES history(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_operations_history ON operations(history_id);
"""


def get_connection() -> sqlite3.Connection:
    # `timeout` is the underlying retry window for a locked DB; we also set
    # the per-connection busy_timeout pragma below for robustness.
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # P1-1: better concurrency so scans / history reads / organize / undo can
    # run without "database is locked" errors under brief lock contention.
    # - busy_timeout: wait up to 5s instead of failing immediately.
    # - WAL: writers don't block readers; survives app restarts safely and is
    #   backward compatible (an existing rollback-journal DB is upgraded on
    #   first open; readers transparently use the -wal file).
    # - synchronous=NORMAL: WAL already guarantees consistency; this avoids
    #   an extra fsync per transaction while keeping durability on checkpoint.
    try:
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
    except sqlite3.OperationalError:
        # Some filesystems (e.g. read-only mounts, certain network shares)
        # reject WAL/busy_timeout. Degrade gracefully — the app still works,
        # just with less concurrency headroom.
        pass
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(_SCHEMA)
