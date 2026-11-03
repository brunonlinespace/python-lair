# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Resolve bundled resources in source, PyInstaller and AppImage modes."""

from __future__ import annotations

import sys
from pathlib import Path


def package_root() -> Path:
    """Return the live python_lair2 package directory."""
    candidates: list[Path] = []

    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        candidates.append(Path(frozen_root) / "python_lair2")

    # Source checkout and PyInstaller module path.
    candidates.append(Path(__file__).resolve().parent.parent)

    # Defensive fallback for PyInstaller one-folder layouts.
    executable_root = Path(sys.executable).resolve().parent
    candidates.extend(
        (
            executable_root / "python_lair2",
            executable_root / "_internal" / "python_lair2",
        )
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


def asset_path(*parts: str) -> Path:
    """Return a path below python_lair2/assets."""
    return package_root().joinpath("assets", *parts)


def icon_path(name: str) -> Path:
    """Return a bundled icon path."""
    return asset_path("icons", name)
