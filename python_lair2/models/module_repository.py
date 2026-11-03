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
models/module_repository.py

Event-driven repository for every Python module.

The repository is the application's single source of truth.
It stores Module objects and emits Qt signals when modules are
added, removed, changed, or reset.

This file contains no widget code.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from .module import Module


class ModuleRepository(QObject):
    """
    Stores and indexes every Module in the workspace.

    Paths are normalized to absolute Path objects so the same file
    cannot accidentally appear in the repository more than once.
    """

    module_added = pyqtSignal(object)
    module_removed = pyqtSignal(object)
    module_changed = pyqtSignal(object)
    module_path_changed = pyqtSignal(object, object)
    repository_reset = pyqtSignal()
    dirty_count_changed = pyqtSignal(int)
    running_count_changed = pyqtSignal(int)

    VALID_SORT_MODES = {
        "title_az",
        "title_za",
        "created",
        "modified",
    }

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._modules: dict[Path, Module] = {}
        self._batch_depth = 0
        self._counts_pending = False

    @staticmethod
    def normalize_path(path: str | Path) -> Path:
        """Return a consistent absolute path without requiring it to exist."""
        return Path(path).expanduser().resolve(strict=False)

    def add(self, module: Module) -> Module:
        """
        Add a module or update the existing object for the same path.

        Returning the stored object ensures callers always use the
        repository's canonical Module instance.
        """
        path = self.normalize_path(module.path)
        module.path = path

        existing = self._modules.get(path)
        if existing is None:
            self._modules[path] = module
            self.module_added.emit(module)
            self._emit_counts()
            return module

        changed = self._copy_metadata(existing, module)
        if changed:
            self.module_changed.emit(existing)
            self._emit_counts()

        return existing

    def add_many(self, modules: Iterable[Module]) -> None:
        """Add or update several modules."""
        for module in modules:
            self.add(module)

    def remove(self, path: str | Path) -> Module | None:
        """Remove and return a module, or return None when absent."""
        normalized = self.normalize_path(path)
        module = self._modules.pop(normalized, None)

        if module is not None:
            self.module_removed.emit(module)
            self._emit_counts()

        return module

    def clear(self) -> None:
        """Remove every module and notify repository observers once."""
        if not self._modules:
            return

        self._modules.clear()
        self.repository_reset.emit()
        self._emit_counts()

    def replace_all(self, modules: Iterable[Module]) -> None:
        """
        Synchronize the repository with a complete filesystem scan.

        Existing Module objects are preserved whenever possible. This is
        important because other parts of the program may hold references
        to them.
        """
        incoming: dict[Path, Module] = {}

        for module in modules:
            path = self.normalize_path(module.path)
            module.path = path
            incoming[path] = module

        existing_paths = set(self._modules)
        incoming_paths = set(incoming)

        # Individual add/remove/change signals still update the relevant UI,
        # while aggregate dirty/running counts are emitted only once.
        with self.batch_update():
            for removed_path in existing_paths - incoming_paths:
                self.remove(removed_path)

            for added_path in incoming_paths - existing_paths:
                self.add(incoming[added_path])

            for shared_path in existing_paths & incoming_paths:
                current = self._modules[shared_path]
                discovered = incoming[shared_path]

                if self._copy_metadata(current, discovered):
                    self.module_changed.emit(current)


    def move_path(
        self,
        old_path: str | Path,
        new_path: str | Path,
        **metadata: object,
    ) -> Module | None:
        """Re-key an existing Module after a successful filesystem rename."""
        old_normalized = self.normalize_path(old_path)
        new_normalized = self.normalize_path(new_path)

        # A drop onto the module's current folder is a no-op, not a path
        # migration. Emitting module_path_changed for an unchanged key can
        # detach a live navigation item unnecessarily.
        if old_normalized == new_normalized:
            module = self._modules.get(old_normalized)
            if module is None:
                return None
            metadata_changed = False
            for name, value in metadata.items():
                if hasattr(module, name) and getattr(module, name) != value:
                    setattr(module, name, value)
                    metadata_changed = True
            module.search_title = module.display_name.casefold()
            module.search_filename = module.filename.casefold()
            if metadata_changed:
                self.module_changed.emit(module)
            self._emit_counts()
            return module

        module = self._modules.pop(old_normalized, None)
        if module is None:
            return None
        if new_normalized in self._modules:
            self._modules[old_normalized] = module
            raise ValueError(f"Repository already contains {new_normalized}")

        module.path = new_normalized
        for name, value in metadata.items():
            if hasattr(module, name):
                setattr(module, name, value)
        module.search_title = module.display_name.casefold()
        module.search_filename = module.filename.casefold()
        self._modules[new_normalized] = module
        self.module_path_changed.emit(module, old_normalized)
        self._emit_counts()
        return module

    def get(self, path: str | Path) -> Module | None:
        """Return a module by path."""
        return self._modules.get(self.normalize_path(path))

    def contains(self, path: str | Path) -> bool:
        """Return True when a path is already known."""
        return self.normalize_path(path) in self._modules

    def all(self) -> tuple[Module, ...]:
        """Return an immutable snapshot of every module."""
        return tuple(self._modules.values())

    def search(self, text: str) -> list[Module]:
        """Search cached title and filename strings."""
        query = text.casefold().strip()

        if not query:
            return list(self._modules.values())

        return [
            module
            for module in self._modules.values()
            if query in module.search_title
            or query in module.search_filename
        ]

    def sorted(
        self,
        modules: Iterable[Module] | None = None,
        mode: str = "modified",
    ) -> list[Module]:
        """Return modules in the requested display order."""
        selected = list(self._modules.values() if modules is None else modules)

        if mode not in self.VALID_SORT_MODES:
            mode = "modified"

        if mode == "title_az":
            return sorted(selected, key=lambda module: module.search_title)

        if mode == "title_za":
            return sorted(
                selected,
                key=lambda module: module.search_title,
                reverse=True,
            )

        if mode == "created":
            return sorted(
                selected,
                key=lambda module: module.created,
                reverse=True,
            )

        return sorted(
            selected,
            key=lambda module: module.modified,
            reverse=True,
        )

    @property
    def dirty(self) -> tuple[Module, ...]:
        """Return modules with unsaved editor changes."""
        return tuple(module for module in self._modules.values() if module.dirty)

    @property
    def running(self) -> tuple[Module, ...]:
        """Return modules whose processes are currently running."""
        return tuple(module for module in self._modules.values() if module.running)

    def set_dirty(self, path: str | Path, dirty: bool) -> bool:
        """Update dirty state and emit a change only when needed."""
        module = self.get(path)
        if module is None or module.dirty == dirty:
            return False

        module.dirty = dirty
        self.module_changed.emit(module)
        self._emit_counts()
        return True

    def set_running(self, path: str | Path, running: bool) -> bool:
        """Update running state and emit a change only when needed."""
        module = self.get(path)
        if module is None or module.running == running:
            return False

        module.running = running
        self.module_changed.emit(module)
        self._emit_counts()
        return True

    @staticmethod
    def _copy_metadata(target: Module, source: Module) -> bool:
        """
        Copy scanner-controlled metadata while preserving runtime state.

        Dirty, loaded, and running are intentionally not overwritten.
        """
        changed = False

        fields = (
            "filename",
            "display_name",
            "folder",
            "created",
            "modified",
            "size",
            "executable",
        )

        for field_name in fields:
            new_value = getattr(source, field_name)
            if getattr(target, field_name) != new_value:
                setattr(target, field_name, new_value)
                changed = True

        new_search_title = target.display_name.casefold()
        new_search_filename = target.filename.casefold()

        if target.search_title != new_search_title:
            target.search_title = new_search_title
            changed = True

        if target.search_filename != new_search_filename:
            target.search_filename = new_search_filename
            changed = True

        return changed

    @contextmanager
    def batch_update(self):
        """Coalesce aggregate count signals during multi-module updates."""
        self._batch_depth += 1
        try:
            yield
        finally:
            self._batch_depth -= 1
            if self._batch_depth == 0 and self._counts_pending:
                self._counts_pending = False
                self._emit_counts_now()

    def _emit_counts(self) -> None:
        if self._batch_depth:
            self._counts_pending = True
            return
        self._emit_counts_now()

    def _emit_counts_now(self) -> None:
        self.dirty_count_changed.emit(len(self.dirty))
        self.running_count_changed.emit(len(self.running))

    def __iter__(self) -> Iterator[Module]:
        return iter(self._modules.values())

    def __len__(self) -> int:
        return len(self._modules)

    def __contains__(self, path: object) -> bool:
        if not isinstance(path, (str, Path)):
            return False
        return self.contains(path)
