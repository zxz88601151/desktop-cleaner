# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Desktop Cleaner (one-file build).
# Equivalent to build.bat; build with:  pyinstaller build.spec
import sys
from pathlib import Path

project_root = Path(SPEC).parent if "SPEC" in globals() else Path.cwd()
src_path = str(project_root / "src")

hiddenimports = [
    "core", "core.classifier", "core.organizer", "core.rules", "core.scanner",
    "core.empty_folders",
    "core.analysis",
    "core.report",
    "core.custom_rules",
    "data", "data.database", "data.settings_repo",
    "data.history_repo", "data.operation_repo",
    "ui", "ui.styles", "ui.dashboard",
    "ui.preview_report", "ui.welcome", "ui.about",
    "ui.themes", "ui.theme_manager",
    "ui.theme", "ui.theme.themes", "ui.theme.theme_manager",
    "ui.state", "ui.widgets", "ui.widgets.controls", "ui.widgets.sidebar",
    "ui.widgets.score_ring", "ui.pages",
    "ui.pages.dashboard_page", "ui.pages.organize_page",
    "ui.pages.custom_page", "ui.pages.history_page", "ui.pages.settings_page",
    "ui.pages.large_files_page", "ui.pages.empty_folders_page",
    "ui.pages.analysis_page",
    "ui.pages.rules_page",
    "ui.pages.tools_page",
    "ui.undo", "ui.app_shell", "ui.coming_soon", "ui.features",
    "ui.icons",
    "version",
    "update", "update.version", "update.constants", "update.manifest",
    "update.checker", "update.decision", "update.integrity",
    "update.manager", "update.update_dialog",
    "utils", "utils.format", "utils.logger", "utils.paths", "utils.errors",
]

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[src_path],
    binaries=[],
    datas=[(str(project_root / "assets" / "author.jpg"), "assets")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# --- Prune the unused Qt Qml / Quick stack --------------------------------
# pyinstaller-hooks-contrib (2026.7) now collects the Qt VirtualKeyboard
# platform-input plugin, and that plugin drags in the whole Qt Qml / Quick
# stack plus Qt6Pdf and Qt6OpenGL: ~19 MB uncompressed / ~9 MB inside the EXE.
#
# This application imports only PySide6.QtWidgets / QtCore / QtGui. The last
# known-good release (built before that hooks upgrade) shipped without any of
# these DLLs, so dropping them simply restores that proven set.
#
# NOTE: the tokens are deliberately specific. "qt6opengl" must NOT be widened
# to "opengl", because PySide6\opengl32sw.dll *is* required -- it is the
# software OpenGL fallback QtWidgets uses when no GPU driver is available.
#
# `excludes=` cannot express this: it filters Python modules only, whereas
# these files are collected as binaries / data by the PySide6 hook. The TOC
# has to be filtered after Analysis instead.
_QT_UNUSED = (
    "qt6qml",                # Qt6Qml, Qt6QmlMeta, Qt6QmlModels, Qt6QmlWorkerScript
    "qt6quick",              # Qt6Quick, Qt6QuickControls2, Qt6QuickWidgets
    "qt6virtualkeyboard",
    "qt6pdf",
    "qt6opengl",             # Qt6OpenGL, Qt6OpenGLWidgets (NOT opengl32sw)
    "qtvirtualkeyboardplugin",
    "qpdf.dll",
)


def _keep_qt_entry(entry) -> bool:
    name = str(entry[0]).lower()
    return not any(token in name for token in _QT_UNUSED)


_pruned = len(a.binaries) + len(a.datas)
a.binaries = [b for b in a.binaries if _keep_qt_entry(b)]
a.datas = [d for d in a.datas if _keep_qt_entry(d)]
_pruned -= len(a.binaries) + len(a.datas)
print(f"[build.spec] pruned {_pruned} unused Qt Qml/Quick/Pdf/OpenGL entries")

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
