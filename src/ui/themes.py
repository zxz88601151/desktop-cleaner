"""Backward-compatible re-export shim for ``ui.theme.themes``.

The real implementation now lives in :mod:`ui.theme.themes` (see the
UI Migration Audit, Phase 0). This module keeps ``import ui.themes``
working so ``main.py``, ``dashboard.py``, ``styles.py`` and the test
suite need no changes during the gradual migration.
"""
from ui.theme.themes import (  # noqa: F401
    DEFAULT_THEME,
    DARK,
    FONT_FAMILY,
    LIGHT,
    MONO_FAMILY,
    QSS_TEMPLATE,
    THEMES,
    build_stylesheet,
    shadow_color,
)
