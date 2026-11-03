# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
"""
Python Lair 2
models/module.py

Pure data model representing one Python script.

This module intentionally contains no Qt imports. UI objects belong in
ModuleState and ModuleStateStore.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Module:
    """Filesystem metadata and application state for one Python script."""

    path: Path
    filename: str
    display_name: str
    folder: str
    created: float
    modified: float
    size: int
    executable: bool

    dirty: bool = False
    loaded: bool = False
    running: bool = False

    search_title: str = field(init=False)
    search_filename: str = field(init=False)

    def __post_init__(self) -> None:
        self.path = Path(self.path).expanduser().resolve(strict=False)
        self.refresh_search_cache()

    @property
    def exists(self) -> bool:
        return self.path.exists()

    @property
    def extension(self) -> str:
        return self.path.suffix

    def refresh_search_cache(self) -> None:
        self.search_title = self.display_name.casefold()
        self.search_filename = self.filename.casefold()

    def update_metadata(
        self,
        *,
        filename: str,
        display_name: str,
        folder: str,
        created: float,
        modified: float,
        size: int,
        executable: bool,
    ) -> bool:
        """Update scanner-controlled metadata and report whether it changed."""
        before = (
            self.filename,
            self.display_name,
            self.folder,
            self.created,
            self.modified,
            self.size,
            self.executable,
        )
        after = (
            filename,
            display_name,
            folder,
            created,
            modified,
            size,
            executable,
        )

        if before == after:
            return False

        (
            self.filename,
            self.display_name,
            self.folder,
            self.created,
            self.modified,
            self.size,
            self.executable,
        ) = after
        self.refresh_search_cache()
        return True

    def __str__(self) -> str:
        return self.display_name

    def __repr__(self) -> str:
        return f"<Module path={self.path!s}>"
