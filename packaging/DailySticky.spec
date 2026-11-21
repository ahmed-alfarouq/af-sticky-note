# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for Daily Sticky.

Packages the application as a standalone Windows directory (onedir)
including PySide6, bundled Thmanyah fonts, initial quotes seed, and app modules.
"""
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

repo_root = Path(SPECPATH).resolve().parent if Path(SPECPATH).name == "packaging" else Path(SPECPATH).resolve()

# Bundled read-only resources
datas = [
    (str(repo_root / "assets" / "logo.png"), "assets"),
    (str(repo_root / "assets" / "icons"), "assets/icons"),
    (str(repo_root / "data" / "quotes.txt"), "data"),
    (str(repo_root / "fonts" / "thmanyah"), "fonts/thmanyah"),
    (str(repo_root / "app" / "database" / "migrations"), "app/database/migrations"),
    # qtawesome icon font (.ttf) + glyph name map (.json); no built-in hook
    # ships them (v3 §1.4). A missing font renders blank buttons in the exe.
    *collect_data_files("qtawesome"),
]

# Every module of the app package is collected automatically, so a new module
# (or a module only imported lazily) is never left out of the executable. The
# build runs in a child process, so the repository root must be on its path.
os.environ["PYTHONPATH"] = os.pathsep.join(
    filter(None, [str(repo_root), os.environ.get("PYTHONPATH", "")])
)
hiddenimports = collect_submodules("app") + [
    "qtawesome",
    "qtpy",
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
