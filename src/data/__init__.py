"""Data access layer for Desktop Cleaner (SQLite)."""
from .database import get_connection, init_db
from .settings_repo import get as get_setting, set as set_setting
from .history_repo import create as create_history, update_status as update_history
from .operation_repo import bulk_insert as insert_operations

__all__ = [
    "get_connection",
    "init_db",
    "get_setting",
    "set_setting",
    "create_history",
    "update_history",
    "insert_operations",
]
