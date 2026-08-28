"""Core business logic for Desktop Cleaner.

Layers:
- rules / classifier : decide *what* a file is
- scanner            : discover & preview files
- organizer          : build & execute the move plan (safe, undoable)
"""
from .classifier import classify
from .organizer import (
    OrganizeResult,
    PlanItem,
    execute_undo,
    move_items,
    organize,
    plan,
    summarize_plan,
    undo_plan,
)
from .rules import category_emoji
from .scanner import ScanResult, scan

__all__ = [
    "classify",
    "OrganizeResult",
    "PlanItem",
    "organize",
    "plan",
    "move_items",
    "execute_undo",
    "undo_plan",
    "summarize_plan",
    "category_emoji",
    "ScanResult",
    "scan",
]
