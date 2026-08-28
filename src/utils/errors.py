"""Map raw Python exceptions to user-friendly, non-technical messages (P1-6).

The full traceback is logged to the file logger by the Worker; only a calm,
actionable sentence reaches the end user (non-technical Chinese users).
"""
from __future__ import annotations

import sqlite3


def friendly_message(exc: Exception) -> str:
    if isinstance(exc, PermissionError):
        return "无法访问该文件夹或文件，请检查权限后重试。"
    if isinstance(exc, FileNotFoundError):
        return "找不到指定的文件或文件夹，可能已被移动或删除。"
    if isinstance(exc, (sqlite3.OperationalError, sqlite3.DatabaseError)):
        msg = str(exc)
        if "locked" in msg.lower():
            return "数据库正忙，请稍后重试。"
        return "整理记录保存失败，请稍后重试。"
    if isinstance(exc, OSError):
        return f"操作未完成：{exc.strerror or exc}。"
    if isinstance(exc, ValueError):
        # Scanner safety guards raise ValueError with a user-facing message.
        return str(exc) or "操作无法完成。"
    return "操作未完成，详细信息已写入日志。"
