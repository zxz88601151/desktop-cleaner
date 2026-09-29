"""Core business logic for Desktop Cleaner.

Layers:
- rules / classifier : decide *what* a file is
- scanner            : discover & preview files
- organizer          : build & execute the move plan (safe, undoable)
- empty_folders      : discover & safely quarantine empty folders (undoable)
- analysis           : read-only structural snapshot of a folder tree
- report             : export an analysis result as JSON / CSV
- custom_rules       : resolve & validate built-in + user rules
"""
from .analysis import AnalysisResult, FileEntry, FolderEntry, analyze
from .classifier import classify
from .custom_rules import (
    Issue,
    RuleConfig,
    UserRule,
    builtin_by_category,
    effective_rules,
    effective_rules_fingerprint,
    load_config,
    normalize_extension,
    reset_config,
    resolve_effective_rules,
    save_config,
    user_rule_origin,
    validate_category,
    validate_config,
    validate_extension,
)
from .empty_folders import (
    CleanupResult,
    EmptyFolder,
    cleanup,
    find_empty_folders,
    plan_cleanup,
    total_nested,
)
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
from .report import (
    REPORT_SCHEMA,
    build_report,
    export,
    supported_formats,
    write_csv,
    write_json,
)
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
    "EmptyFolder",
    "CleanupResult",
    "find_empty_folders",
    "plan_cleanup",
    "total_nested",
    "cleanup",
    "AnalysisResult",
    "FileEntry",
    "FolderEntry",
    "analyze",
    "REPORT_SCHEMA",
    "build_report",
    "export",
    "supported_formats",
    "write_csv",
    "write_json",
    "Issue",
    "RuleConfig",
    "UserRule",
    "builtin_by_category",
    "effective_rules",
    "effective_rules_fingerprint",
    "load_config",
    "normalize_extension",
    "reset_config",
    "resolve_effective_rules",
    "save_config",
    "user_rule_origin",
    "validate_category",
    "validate_config",
    "validate_extension",
]
