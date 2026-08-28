"""Backward-compatible re-export shim for ``ui.theme.theme_manager``.

The real implementation now lives in :mod:`ui.theme.theme_manager` (see
the UI Migration Audit, Phase 0). This module keeps ``import
ui.theme_manager`` working so ``main.py``, ``main_window.py`` and
``dashboard.py`` need no changes during the gradual migration.
"""
from ui.theme.theme_manager import ThemeManager  # noqa: F401
