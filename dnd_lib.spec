# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for D&D SRD Library.

Build with:
    pyinstaller dnd_lib.spec

Or via the helper script:
    python scripts/build.py
"""

from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821 – SPECPATH is injected by PyInstaller

# ---------------------------------------------------------------------------
# Data files to bundle
# ---------------------------------------------------------------------------
# Tuples of (source, destination-inside-bundle)
datas = [
    # Read-only SRD JSON data
    (str(ROOT / "data" / "2014"), "data/2014"),
    # Web assets
    (str(ROOT / "src" / "dnd_lib" / "static"), "static"),
    (str(ROOT / "src" / "dnd_lib" / "templates"), "templates"),
]

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    [str(ROOT / "src" / "dnd_lib" / "tray.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "waitress",
        "waitress.task",
        "waitress.channel",
        "waitress.server",
        "pystray",
        "pystray._base",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
        "platformdirs",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821

# ---------------------------------------------------------------------------
# Executable
# ---------------------------------------------------------------------------
_icon_ico = str(ROOT / "src" / "dnd_lib" / "static" / "icon.ico")
_icon_png = str(ROOT / "src" / "dnd_lib" / "static" / "icon.png")

import platform as _platform  # noqa: E402
_icon = _icon_ico if _platform.system() == "Windows" else _icon_png

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="dnd_lib",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # No console window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
)
