"""Theme manager (UI refactor, V1.2).

A tiny singleton that owns the active theme, renders the stylesheet via
:mod:`ui.themes`, applies it to the ``QApplication``, and persists the
choice in the existing settings KV store (no schema change).

Non-business: it only reads/writes a ``theme`` setting key.
"""
from __future__ import annotations

from PySide6.QtWidgets import QApplication

from data import settings_repo
from ui.themes import DEFAULT_THEME, THEMES, build_stylesheet, shadow_color


class ThemeManager:
    _instance: "ThemeManager | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init(self):
        self._theme = settings_repo.get("theme", DEFAULT_THEME) or DEFAULT_THEME
        if self._theme not in THEMES:
            self._theme = DEFAULT_THEME
        self._app: QApplication | None = None
        self._callbacks: list[callable] = []

    # ----- public API --------------------------------------------------- #
    def apply(self, app: QApplication) -> None:
        self._app = app
        app.setStyleSheet(self.stylesheet)

    @property
    def stylesheet(self) -> str:
        return build_stylesheet(self._theme)

    @property
    def theme(self) -> str:
        return self._theme

    @property
    def is_dark(self) -> bool:
        return self._theme == "dark"

    def shadow_color(self):
        return shadow_color(self._theme)

    def set_theme(self, name: str) -> None:
        if name not in THEMES or name == self._theme:
            return
        self._theme = name
        settings_repo.set("theme", name)
        if self._app is not None:
            self._app.setStyleSheet(self.stylesheet)
        self._emit()

    def toggle(self) -> None:
        self.set_theme("dark" if self._theme == "light" else "light")

    def on_changed(self, cb: callable) -> None:
        """Register a callback invoked after the theme changes."""
        if cb not in self._callbacks:
            self._callbacks.append(cb)

    def _emit(self):
        for cb in self._callbacks:
            cb()
