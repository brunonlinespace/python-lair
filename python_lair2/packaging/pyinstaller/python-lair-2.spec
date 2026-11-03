# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller one-folder bundle for Python Lair 2."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

package_root = Path(SPECPATH).resolve().parents[1]
project_root = package_root.parent

# PyQt6 is the only Qt binding used by the application. Explicit exclusions
# prevent accidental collection of another binding from the build environment.
excluded_qt_bindings = ["PySide2", "PySide6", "PyQt5"]

hiddenimports = collect_submodules("python_lair2")
hiddenimports += [
    "PyQt6.QtSvg",
    "PyQt6.QtSvgWidgets",
]

datas = [
    (str(package_root / "assets"), "python_lair2/assets"),
    (str(package_root / "LICENSE"), "."),
    (str(package_root / "docs" / "README.md"), "."),
    (str(package_root / "docs" / "RELEASE_NOTES.md"), "."),
]

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_qt_bindings,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="python-lair-2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="python-lair-2",
)
