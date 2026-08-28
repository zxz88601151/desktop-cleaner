"""Persist each organize run as a history record."""
from __future__ import annotations

import datetime
from typing import Optional

from .database import get_connection


def create(source_path: str, mode: str, total_files: int = 0) -> int:
    now = datetime.datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO history(source_path, mode, total_files, organized_files, "
            "skipped_files, status, created_at) VALUES (?, ?, ?, 0, 0, 'running', ?)",
            (str(source_path), mode, total_files, now),
        )
        return int(cur.lastrowid)


def update_status(hid: int, status: str, organized: int = 0, skipped: int = 0) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE history SET status=?, organized_files=?, skipped_files=? WHERE id=?",
            (status, organized, skipped, hid),
        )


def get(hid: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM history WHERE id = ?", (hid,)).fetchone()
        return dict(row) if row else None


def list_all(limit: int = 50) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def latest_done() -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM history WHERE status='done' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def get_stats() -> dict:
    """Aggregate dashboard statistics from the history table.

    - total_files: sum of files organized in *successful* runs (status='done')
    - runs:        number of completed organize runs (done or later undone)
    - last_time:   timestamp of the most recent completed run, or None

    Read-only; does not alter the schema or any row.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(organized_files), 0) AS total_files, "
            "COUNT(*) AS runs, MAX(created_at) AS last_time "
            "FROM history WHERE status IN ('done', 'undone')"
        ).fetchone()
        return {
            "total_files": int(row["total_files"]),
            "runs": int(row["runs"]),
            "last_time": row["last_time"],
        }
