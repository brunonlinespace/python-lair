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
models/module_state.py

Qt-facing runtime state for one module.

Keeping this separate from Module prevents the pure data model from depending
on widgets, editors, tree items, or processes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QTreeWidgetItem, QWidget

if TYPE_CHECKING:
    from python_lair2.widgets.code_editor import CodeEditor


@dataclass(slots=True)
class ModuleState:
    """Lazily-created UI and process objects associated with one module."""

    editor: CodeEditor | None = None
    editor_page: QWidget | None = None
    dashboard_card: QWidget | None = None
    dashboard_grid_card: QWidget | None = None
    tree_item: QTreeWidgetItem | None = None
    process: QProcess | None = None

    page_created: bool = False

    def has_editor(self) -> bool:
        return self.editor is not None

    def has_running_process(self) -> bool:
        return (
            self.process is not None
            and self.process.state() != QProcess.ProcessState.NotRunning
        )

    def clear_editor(self) -> None:
        self.editor = None
        self.editor_page = None
        self.page_created = False

    def clear_views(self) -> None:
        self.dashboard_card = None
        self.dashboard_grid_card = None
        self.tree_item = None
        self.clear_editor()

    def clear_process(self) -> None:
        self.process = None
