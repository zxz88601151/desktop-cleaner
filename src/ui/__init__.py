"""UI layer for Desktop Cleaner (PySide6).

The Premium app shell lives in :mod:`ui.app_shell`; individual pages are
under :mod:`ui.pages`. This package root is intentionally import-light so
that importing ``ui`` (e.g. for ``ui.theme_manager``) never pulls in a
heavy window module.
"""
