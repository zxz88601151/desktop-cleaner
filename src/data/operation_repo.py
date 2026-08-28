"""Persist every individual file move so it can be undone."""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import List, Set

from .database import get_connection
from core.organizer import OrganizeResult, PlanItem


def bulk_insert(hid: int, items: List[PlanItem]) -> None:
    now = datetime.datetime.now().isoformat(timespec="seconds")
    rows = [
        (hid, str(it.source), str(it.target), it.source.name, it.category, "moved", now)
        for it in items
    ]
    with get_connection() as conn:
        conn.executemany(
            "INSERT INTO operations(history_id, source_path, target_path, file_name, "
            "category, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )


def bulk_insert_pending(hid: int, items: List[PlanItem]) -> None:
    """P0-1: record the planned moves as ``pending`` *before* touching files.

    This guarantees that even if the process is killed mid-organize, every
    intended move is represented in the DB and can later be reconciled.
    """
    now = datetime.datetime.now().isoformat(timespec="seconds")
    rows = [
        (hid, str(it.source), str(it.target), it.source.name, it.category, "pending", now)
        for it in items
    ]
    with get_connection() as conn:
        conn.executemany(
            "INSERT INTO operations(history_id, source_path, target_path, file_name, "
            "category, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )


def update_statuses_by_target(
    hid: int, moved_targets: Set[str], failed_targets: Set[str]
) -> None:
    """P0-1: settle pending operations to ``moved`` / ``failed`` after the run.

    Keys are ``target_path`` values produced by :func:`core.organizer.plan`,
    which are identical to those inserted by :func:`bulk_insert_pending`.
    """
    with get_connection() as conn:
        conn.executemany(
            "UPDATE operations SET status='moved' WHERE history_id=? AND target_path=?",
            [(hid, t) for t in moved_targets],
        )
        conn.executemany(
            "UPDATE operations SET status='failed' WHERE history_id=? AND target_path=?",
            [(hid, t) for t in failed_targets],
        )


def apply_undo_result(hid: int, result: OrganizeResult) -> List[str]:
    """P0-2: mark only successfully-restored operations as ``undone``.

    Operations whose file was *not* moved back (present in ``result.errors``)
    keep their ``moved`` status so the user can retry later. Returns the list
    of failure messages (empty when the undo was fully successful).

    P1-2: the status writes are collected and applied in a single
    ``executemany`` instead of one ``execute`` per operation.
    """
    restored = {str(it.target) for it in result.items}
    undone_ids: List[int] = []
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM operations WHERE history_id=?", (hid,)
        ).fetchall()
        for op in rows:
            if op["source_path"] in restored:
                undone_ids.append(op["id"])
        if undone_ids:
            conn.executemany(
                "UPDATE operations SET status='undone' WHERE id=?",
                [(i,) for i in undone_ids],
            )
    return list(result.errors)


def reconcile_pending() -> int:
    """P0-1 startup recovery: calibrate ``pending`` ops against the file system.

    Only *checks* state — never moves files:
      - target exists & source gone   -> moved   (the move did happen)
      - otherwise (source present)    -> failed  (the move did not happen)

    Dangling ``running`` history records (killed mid-run) are settled to
    ``done`` when they hold at least one moved op and no pending op left, so
    the moved files remain undoable. Returns the number of ops reconciled.
    """
    settled = 0
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM operations WHERE status='pending'"
        ).fetchall()
        for r in rows:
            src = Path(r["source_path"])
            tgt = Path(r["target_path"])
            if tgt.exists() and not src.exists():
                conn.execute(
                    "UPDATE operations SET status='moved' WHERE id=?", (r["id"],)
                )
            else:
                conn.execute(
                    "UPDATE operations SET status='failed' WHERE id=?", (r["id"],)
                )
            settled += 1

        running = conn.execute(
            "SELECT * FROM history WHERE status='running'"
        ).fetchall()
        for h in running:
            hid = h["id"]
            op_rows = conn.execute(
                "SELECT status FROM operations WHERE history_id=?", (hid,)
            ).fetchall()
            if not op_rows:
                continue
            statuses = {r["status"] for r in op_rows}
            if "pending" in statuses:
                continue
            moved = sum(1 for s in op_rows if s["status"] == "moved")
            failed = sum(1 for s in op_rows if s["status"] == "failed")
            total = h["total_files"] or 0
            skipped = max(total - moved - failed, 0)
            conn.execute(
                "UPDATE history SET status='done', organized_files=?, "
                "skipped_files=? WHERE id=?",
                (moved, skipped, hid),
            )
    return settled


def list_by_history(hid: int) -> List[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM operations WHERE history_id = ? ORDER BY id", (hid,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_status(op_id: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE operations SET status = ? WHERE id = ?", (status, op_id)
        )
