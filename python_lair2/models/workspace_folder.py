# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
"""Pure data model for a workspace subfolder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WorkspaceFolder:
    """Represents one directory contained by the active workspace."""

    path: Path
    workspace_root: Path

    def __post_init__(self) -> None:
        path = self.path.expanduser().resolve(strict=False)
        root = self.workspace_root.expanduser().resolve(strict=False)
        path.relative_to(root)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "workspace_root", root)

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def relative_path(self) -> Path:
        return self.path.relative_to(self.workspace_root)

    @property
    def is_workspace_root(self) -> bool:
        return self.path == self.workspace_root

    def contains(self, path: str | Path) -> bool:
        try:
            Path(path).expanduser().resolve(strict=False).relative_to(self.path)
            return True
        except ValueError:
            return False
