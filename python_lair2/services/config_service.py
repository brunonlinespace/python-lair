# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
"""Persistent application settings for Python Lair 2."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from python_lair2.services.file_io import (
    FileTooLargeError,
    UnsupportedFileError,
    absolute_user_path,
    ensure_private_directory,
    fsync_directory,
    read_regular_file,
)


class ConfigService:
    """Load and save a small JSON configuration file safely."""

    MAX_CONFIG_BYTES = 1024 * 1024

    DEFAULTS: dict[str, Any] = {
        "dashboard_sort": "modified",
        "dashboard_search": "",
        "dashboard_view": "list",
        "window_width": 1350,
        "window_height": 850,
        "window_maximized": False,
        "splitter_sizes": [260, 1090],
        "collapsed_folders": [],
        "last_opened_script": None,
        "last_opened_folder": None,
        "workspace_path": None,
        "setup_completed": False,
        "show_setup_assistant": False,
        # Sheepy-derived editor/runtime preferences. View Only deliberately
        # remains session-local and is not persisted.
        "editor_word_wrap": False,
        "editor_line_numbers": True,
        "show_status_bar": True,
        "editor_font_family": "",
        "editor_font_size": 10,
        "editor_font_weight": 400,
        "editor_font_italic": False,
        "editor_tab_width_spaces": 4,
        "interpreter_override": "",
        "environment_profiles": {"Default": {}},
        "active_environment_profile": "Default",
        "working_directory_mode": "script",
        "custom_working_directory": "",
        "last_run_arguments": "",
        "last_run_in_terminal": False,
    }

    def __init__(self, path: str | Path) -> None:
        self.path = absolute_user_path(path)
        self._data: dict[str, Any] = copy.deepcopy(self.DEFAULTS)
        self.load()

    def load(self) -> None:
        self._data = copy.deepcopy(self.DEFAULTS)
        try:
            raw, _snapshot = read_regular_file(
                self.path,
                self.MAX_CONFIG_BYTES,
                follow_symlinks=False,
            )
            loaded = json.loads(raw.decode("utf-8"))
            if isinstance(loaded, dict):
                self._data.update(loaded)
        except (
            FileNotFoundError,
            FileTooLargeError,
            UnsupportedFileError,
            UnicodeDecodeError,
            OSError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ):
            # A damaged, oversized, or unsafe config must never prevent startup.
            self._data = copy.deepcopy(self.DEFAULTS)

    def save(self) -> bool:
        temporary: Path | None = None
        descriptor: int | None = None
        try:
            ensure_private_directory(self.path.parent)
            descriptor, raw_path = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
                text=True,
            )
            temporary = Path(raw_path)
            if hasattr(os, "fchmod"):
                os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                descriptor = None
                json.dump(self._data, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            temporary = None
            fsync_directory(self.path.parent)
            return True
        except OSError:
            return False
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if temporary is not None:
                try:
                    temporary.unlink()
                except OSError:
                    pass

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any, *, save: bool = False) -> None:
        self._data[key] = value
        if save:
            self.save()

    def update(self, values: dict[str, Any], *, save: bool = False) -> None:
        self._data.update(values)
        if save:
            self.save()

    def get_int(
        self,
        key: str,
        default: int,
        *,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int:
        """Return a validated integer without trusting edited JSON values."""
        try:
            value = int(self._data.get(key, default))
        except (TypeError, ValueError):
            value = default
        if minimum is not None:
            value = max(minimum, value)
        if maximum is not None:
            value = min(maximum, value)
        return value

    def get_int_list(
        self,
        key: str,
        default: list[int],
        *,
        length: int | None = None,
    ) -> list[int]:
        """Return a validated list of non-negative integers."""
        raw = self._data.get(key, default)
        if not isinstance(raw, list) or (length is not None and len(raw) != length):
            return list(default)
        try:
            values = [max(0, int(value)) for value in raw]
        except (TypeError, ValueError):
            return list(default)
        return values

