"""Backward-compatible stylesheet entry point.

The active theme is now owned by :class:`ui.theme_manager.ThemeManager`.
This module still exports ``STYLESHEET`` (the light theme) so any legacy
import keeps working, but new code should apply the theme via the manager.
"""
from __future__ import annotations

from ui.themes import build_stylesheet

STYLESHEET = build_stylesheet("light")
