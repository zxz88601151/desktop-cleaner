# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Desktop Cleaner (one-file build).
# Equivalent to build.bat; build with:  pyinstaller build.spec
import sys
from pathlib import Path

project_root = Path(SPEC).parent if "SPEC" in globals() else Path.cwd()
src_path = str(project_root / "src")

hiddenimports = [
    "core", "core.classifier", "core.organizer", "core.rules", "core.scanner",
    "data", "data.database", "data.settings_repo",
    "data.history_repo", "data.operation_repo",
    "ui", "ui.styles", "ui.dashboard",
    "ui.preview_report", "ui.welcome", "ui.about",
    "ui.themes", "ui.theme_manager",
    "ui.theme", "ui.theme.themes", "ui.theme.theme_manager",
    "ui.state", "ui.widgets", "ui.widgets.controls", "ui.pages",
    "ui.pages.dashboard_page", "ui.pages.organize_page",
    "ui.pages.custom_page", "ui.pages.history_page", "ui.pages.settings_page",
    "ui.pages.tools_page",
    "ui.undo", "ui.app_shell", "ui.coming_soon", "ui.features",
    "version",
    "update", "update.version", "update.constants", "update.manifest",
    "update.checker", "update.decision", "update.integrity",
    "update.manager", "update.update_dialog",
    "utils", "utils.format", "utils.logger",
]

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[src_path],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DesktopCleaner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
