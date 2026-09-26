# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for Daily Sticky.

Packages the application as a standalone Windows directory (onedir)
including PySide6, bundled Thmanyah fonts, initial quotes seed, and app modules.
"""
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

repo_root = Path(SPECPATH).resolve().parent if Path(SPECPATH).name == "packaging" else Path(SPECPATH).resolve()

# Bundled read-only resources
datas = [
    (str(repo_root / "data" / "quotes.txt"), "data"),
    (str(repo_root / "fonts" / "thmanyah"), "fonts/thmanyah"),
    (str(repo_root / "app" / "database" / "migrations"), "app/database/migrations"),
]

hiddenimports = [
    "app",
    "app.config",
    "app.config.settings",
    "app.core",
    "app.core.models",
    "app.core.daily_stats",
    "app.core.services",
    "app.core.services.daily_lifecycle_coordinator",
    "app.core.services.daily_rollover_service",
    "app.core.services.history_service",
    "app.core.services.quote_import_service",
    "app.core.services.quote_service",
    "app.core.services.task_service",
    "app.database",
    "app.database.connection",
    "app.database.day_repository",
    "app.database.migrations",
    "app.database.quote_repository",
    "app.database.quote_rotation_state_repository",
    "app.database.quote_usage_repository",
    "app.database.task_repository",
    "app.database.transaction",
    "app.database.unit_of_work",
    "app.infrastructure",
    "app.infrastructure.clock",
    "app.infrastructure.fonts",
    "app.infrastructure.paths",
    "app.infrastructure.quotes_file",
    "app.platform",
    "app.platform.interfaces",
    "app.platform.provider",
    "app.platform.unsupported",
    "app.platform.windows",
    "app.platform.windows.desktop_window",
    "app.platform.windows.native",
    "app.platform.windows.startup",
    "app.platform.windows.tray",
    "app.ui",
    "app.ui.geometry_manager",
    "app.ui.styles",
    "app.ui.styles.app_style",
    "app.ui.widgets",
    "app.ui.widgets.quote_widget",
    "app.ui.widgets.task_edit_dialog",
    "app.ui.widgets.task_input",
    "app.ui.widgets.task_item",
    "app.ui.widgets.task_list",
    "app.ui.windows",
    "app.ui.windows.history_window",
    "app.ui.windows.main_window",
    "app.ui.windows.settings_window",
    "sqlite3",
]

a = Analysis(
    [str(repo_root / "run.py")],
    pathex=[str(repo_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "_pytest", "unittest", "tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DailySticky",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed GUI app (no cmd window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DailySticky",
)
