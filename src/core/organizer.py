"""Organize files: build a move plan and execute it safely.

Design notes (safety first):
- Files are *moved*, never deleted.
- Target collisions are resolved by renaming (``name (1).ext``), never overwriting.
- Every move is recorded so it can be undone later.
"""
from __future__ import annotations

import datetime
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .classifier import classify
from .rules import DEFAULT_RULES, category_display, category_emoji
from .scanner import _date_label, scan
from utils.logger import get_logger
from utils.paths import win_long

_log = get_logger("organizer")

ProgressCb = Callable[[int, int, str], None]


@dataclass
class PlanItem:
    source: Path
    target: Path
    category: str  # display label of the destination folder


@dataclass
class OrganizeResult:
    total: int = 0
    moved: int = 0
    skipped: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)
    items: List[PlanItem] = field(default_factory=list)  # successfully moved
    failed_items: List[PlanItem] = field(default_factory=list)  # failed to move
    # P1-4: structured per-failure detail for user-facing diagnostics / logs.
    failed_details: List[dict] = field(default_factory=list)


def _unique_target(target: Path) -> Path:
    """Return *target*, renamed with a numeric suffix if it already exists.

    Existence checks use the long-path-safe form (P1-5) so deeply nested
    targets are evaluated correctly; the returned value stays a plain
    ``Path`` so downstream code (which re-applies ``win_long`` at the actual
    ``shutil.move`` call) remains consistent.
    """
    if not os.path.exists(win_long(target)):
        return target
    stem = target.stem
    suffix = target.suffix
    i = 1
    while True:
        candidate = target.parent / f"{stem} ({i}){suffix}"
        if not os.path.exists(win_long(candidate)):
            return candidate
        i += 1


def _category_label(path: Path, mode: str, rules) -> str:
    if mode == "date":
        return _date_label(path)
    return category_display(classify(path, rules))


def plan(
    root: Path,
    mode: str = "type",
    recursive: bool = False,
    rules: Optional[Dict[str, str]] = None,
) -> List[PlanItem]:
    """Build the list of moves without executing them."""
    rules = rules or DEFAULT_RULES
    scan_result = scan(root, mode=mode, recursive=recursive, rules=rules)
    items: List[PlanItem] = []
    # P1-3: de-duplicate by the as-listed source path so a file can only ever
    # yield one move plan. We deliberately do NOT resolve symlinks here — that
    # would wrongly merge a symlink with its target and could drop a legitimate
    # file from the plan.
    seen: set = set()
    for f in scan_result.files:
        key = str(f)
        if key in seen:
            continue
        seen.add(key)
        label = _category_label(f, mode, rules)
        target_dir = Path(root) / label
        target = _unique_target(target_dir / f.name)
        items.append(PlanItem(source=f, target=target, category=label))
    return items


def summarize_plan(items: List[PlanItem], root: Path) -> dict:
    """Aggregate a plan into a report-friendly structure (no side effects).

    Used by the pre-organize *simulation report* so the user can see exactly
    what will happen before any file is moved.
    """
    root = Path(root)
    categories: Dict[str, dict] = {}
    for it in items:
        label = it.category
        cat = categories.setdefault(
            label,
            {
                "label": label,
                "emoji": category_emoji(label),
                "target": str(root / label),
                "count": 0,
                "size": 0,
                "samples": [],
            },
        )
        try:
            size = it.source.stat().st_size
        except OSError:
            size = 0
        cat["count"] += 1
        cat["size"] += size
        if len(cat["samples"]) < 200:
            try:
                rel = Path(it.target).relative_to(root)
            except ValueError:
                rel = Path(it.target).name
            cat["samples"].append((it.source.name, str(rel)))
    cat_list = sorted(categories.values(), key=lambda c: c["count"], reverse=True)
    return {
        "root": str(root),
        "total": len(items),
        "total_size": sum(c["size"] for c in cat_list),
        "categories": cat_list,
    }


def move_items(
    items: List[PlanItem],
    on_progress: Optional[ProgressCb] = None,
) -> OrganizeResult:
    """Execute a pre-built move plan with per-file verification.

    For every item: create the target directory, move the file, then verify
    the move actually happened (target exists & source gone). Failures are
    recorded (status stays ``failed`` at the DB layer) instead of aborting
    the whole run. Files are never deleted or overwritten.
    """
    total = len(items)
    result = OrganizeResult(total=total)
    for i, item in enumerate(items, 1):
        try:
            # P1-5: create the (possibly very deep) target directory using the
            # long-path-safe form too — otherwise a >260-char target parent
            # fails with WinError 3 before the move even starts.
            os.makedirs(win_long(item.target.parent), exist_ok=True)
            # P1-5: use the long-path-safe form for the actual move.
            src = win_long(item.source)
            tgt = win_long(item.target)
            shutil.move(src, tgt)
            if os.path.exists(tgt) and not os.path.exists(src):
                result.moved += 1
                result.items.append(item)
            else:
                raise OSError(f"move verification failed: {item.source.name}")
        except Exception as exc:  # noqa: BLE001 - surface every failure
            result.failed += 1
            result.failed_items.append(item)
            # P1-4: structured, user-facing failure record (source / target /
            # operation / error_type / error_message / timestamp) and a single
            # line written to the application log file.
            detail = {
                "source": str(item.source),
                "target": str(item.target),
                "operation": "move",
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            }
            result.failed_details.append(detail)
            result.errors.append(f"{item.source.name}: {exc}")
            _log.error(
                "MOVE FAILED src=%s tgt=%s type=%s msg=%s",
                item.source, item.target, type(exc).__name__, exc,
            )
        if on_progress:
            on_progress(i, total, f"处理: {item.source.name}")
    result.skipped = result.total - result.moved - result.failed
    _log.info(
        "MOVE BATCH done total=%d moved=%d failed=%d skipped=%d",
        result.total, result.moved, result.failed, result.skipped,
    )
    return result


def organize(
    root: Path,
    mode: str = "type",
    recursive: bool = False,
    rules: Optional[Dict[str, str]] = None,
    on_progress: Optional[ProgressCb] = None,
) -> OrganizeResult:
    """Execute the organization and return a summary.

    Builds the plan via :func:`plan` and executes it with
    :func:`move_items`. Files are moved into ``<root>/<category>/``
    sub-folders. Pure with respect to the file system except for moves.
    """
    root = Path(root)
    rules = rules or DEFAULT_RULES
    items = plan(root, mode=mode, recursive=recursive, rules=rules)
    return move_items(items, on_progress=on_progress)


def undo_plan(operations: List[dict]) -> List[PlanItem]:
    """Build a plan that moves previously-moved files back to their origin."""
    items: List[PlanItem] = []
    for op in operations:
        if op.get("status") != "moved":
            continue
        source = Path(op["target_path"])
        # P0-3: collision-safe restore target (never overwrite an existing file)
        target = _unique_target(Path(op["source_path"]))
        items.append(PlanItem(source=source, target=target, category=op["category"]))
    return items


def execute_undo(
    operations: List[dict],
    on_progress: Optional[ProgressCb] = None,
) -> OrganizeResult:
    """Move files back to their original location. Returns a summary.

    Reuses :func:`move_items` so restore operations are verified the same
    way as organize operations (no overwrite, no deletion).
    """
    items = undo_plan(operations)
    return move_items(items, on_progress=on_progress)
