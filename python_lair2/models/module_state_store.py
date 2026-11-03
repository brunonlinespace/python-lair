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
models/module_state_store.py

Stores Qt runtime state separately from ModuleRepository.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

from .module import Module
from .module_repository import ModuleRepository
from .module_state import ModuleState


class ModuleStateStore(QObject):
    """Owns one ModuleState per repository module path."""

    state_created = pyqtSignal(object, object)
    state_removed = pyqtSignal(object, object)
    states_reset = pyqtSignal()

    def __init__(
        self,
        repository: ModuleRepository,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.repository = repository
        self._states: dict[Path, ModuleState] = {}

        repository.module_added.connect(self._on_module_added)
        repository.module_removed.connect(self._on_module_removed)
        repository.module_path_changed.connect(self._on_module_path_changed)
        repository.repository_reset.connect(self.clear)

        for module in repository:
            self.ensure(module.path)

    def ensure(self, path: str | Path) -> ModuleState:
        """Return the state for a path, creating it when necessary."""
        normalized = self.repository.normalize_path(path)
        state = self._states.get(normalized)

        if state is None:
            state = ModuleState()
            self._states[normalized] = state
            module = self.repository.get(normalized)
            if module is not None:
                self.state_created.emit(module, state)

        return state

    def get(self, path: str | Path) -> ModuleState | None:
        normalized = self.repository.normalize_path(path)
        return self._states.get(normalized)


    def move_path(
        self,
        old_path: str | Path,
        new_path: str | Path,
    ) -> ModuleState | None:
        """Re-key UI/runtime state after a module rename."""
        old_normalized = self.repository.normalize_path(old_path)
        new_normalized = self.repository.normalize_path(new_path)
        state = self._states.pop(old_normalized, None)
        if state is not None:
            self._states[new_normalized] = state
        return state

    def remove(self, path: str | Path) -> ModuleState | None:
        normalized = self.repository.normalize_path(path)
        state = self._states.pop(normalized, None)
        return state

    def clear(self) -> None:
        if not self._states:
            return

        for state in self._states.values():
            process = state.process
            if process is not None and process.state() != QProcess.ProcessState.NotRunning:
                process.terminate()

        self._states.clear()
        self.states_reset.emit()

    def _on_module_added(self, module: Module) -> None:
        self.ensure(module.path)


    def _on_module_path_changed(self, module: Module, old_path: Path) -> None:
        """Move existing runtime state to the module's new repository key."""
        self.move_path(old_path, module.path)

    def _on_module_removed(self, module: Module) -> None:
        state = self.remove(module.path)
        if state is None:
            return

        process = state.process
        if process is not None and process.state() != QProcess.ProcessState.NotRunning:
            process.terminate()

        self.state_removed.emit(module, state)

    def __iter__(self) -> Iterator[tuple[Path, ModuleState]]:
        return iter(self._states.items())

    def __len__(self) -> int:
        return len(self._states)
