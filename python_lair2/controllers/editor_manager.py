# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
"""Coordinates dashboard, folder dashboards, and lazy editor pages."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget

from python_lair2.models.module import Module
from python_lair2.models.workspace_folder import WorkspaceFolder
from python_lair2.widgets.dashboard import DashboardWidget
from python_lair2.widgets.editor_page import EditorPage
from python_lair2.widgets.folder_dashboard import FolderDashboard


class EditorManager(QObject):
    current_module_changed = pyqtSignal(object)
    current_folder_changed = pyqtSignal(object)
    dashboard_shown = pyqtSignal()
    status_message = pyqtSignal(str)
    launch_requested = pyqtSignal(object)
    terminal_requested = pyqtSignal(object)
    stop_requested = pyqtSignal(object)
    force_stop_requested = pyqtSignal(object)
    admin_terminal_requested = pyqtSignal(object)
    run_with_arguments_requested = pyqtSignal(object)
    syntax_lint_requested = pyqtSignal(object)
    interpreter_requested = pyqtSignal(object)
    working_directory_requested = pyqtSignal(object)
    environment_profiles_requested = pyqtSignal(object)
    external_editor_requested = pyqtSignal(object)
    containing_folder_requested = pyqtSignal(object)
    rename_requested = pyqtSignal(object)
    executable_toggle_requested = pyqtSignal(object)
    remove_requested = pyqtSignal(object)
    duplicate_requested = pyqtSignal(object)
    editor_history_changed = pyqtSignal(bool, bool)
    editor_preferences_changed = pyqtSignal()
    folder_open_external_requested = pyqtSignal(object)
    folder_terminal_requested = pyqtSignal(object)
    folder_rename_requested = pyqtSignal(object)
    folder_remove_requested = pyqtSignal(object)
    create_script_requested = pyqtSignal(object)
    create_folder_requested = pyqtSignal(object)
    external_files_import_requested = pyqtSignal(object, object)
    refresh_requested = pyqtSignal()
    sort_mode_changed = pyqtSignal(str)
    view_mode_changed = pyqtSignal(str)

    def __init__(self, library_root, repository, states, stack, config, parent=None) -> None:
        super().__init__(parent)
        self.library_root = Path(library_root).expanduser().resolve(strict=False)
        self.repository = repository
        self.states = states
        self.stack = stack
        self.config = config
        self.current_module: Module | None = None
        self.current_folder: Path | None = None
        self._folder_pages: dict[Path, FolderDashboard] = {}
        self.dashboard = DashboardWidget(repository, states, stack)
        self.stack.addWidget(self.dashboard)
        self._connect_dashboard()
        states.state_removed.connect(self._on_state_removed)
        repository.repository_reset.connect(self._on_repository_reset)
        self.show_dashboard()

    def _connect_dashboard(self) -> None:
        self.dashboard.module_open_requested.connect(self.open_module)
        self.dashboard.module_launch_requested.connect(self.launch_requested)
        self.dashboard.module_terminal_requested.connect(self.terminal_requested)
        self.dashboard.module_stop_requested.connect(self.stop_requested)
        self.dashboard.module_force_stop_requested.connect(self.force_stop_requested)
        self.dashboard.module_remove_requested.connect(self.remove_requested)
        self.dashboard.create_script_requested.connect(
            lambda: self.create_script_requested.emit(self.library_root)
        )
        self.dashboard.create_folder_requested.connect(
            lambda: self.create_folder_requested.emit(self.library_root)
        )
        self.dashboard.refresh_requested.connect(self.refresh_requested)
        self.dashboard.sort_mode_changed.connect(self.sort_mode_changed)
        self.dashboard.view_mode_changed.connect(self.view_mode_changed)

    def show_dashboard(self) -> None:
        self.current_module = None; self.current_folder = None
        self.stack.setCurrentWidget(self.dashboard)
        self.dashboard_shown.emit()

    def open_folder(self, path) -> FolderDashboard | None:
        folder_path = Path(path).expanduser().resolve(strict=False)
        try: folder_path.relative_to(self.library_root)
        except ValueError:
            self.status_message.emit("The selected folder is outside the workspace.")
            return None
        if not folder_path.is_dir():
            self.status_message.emit("The selected folder is no longer available.")
            return None
        page = self._folder_pages.get(folder_path)
        if page is None:
            page = FolderDashboard(WorkspaceFolder(folder_path, self.library_root), self.repository, self.stack)
            page.module_open_requested.connect(self.open_module)
            page.module_launch_requested.connect(self.launch_requested)
            page.module_terminal_requested.connect(self.terminal_requested)
            page.module_stop_requested.connect(self.stop_requested)
            page.module_force_stop_requested.connect(self.force_stop_requested)
            page.module_remove_requested.connect(self.remove_requested)
            page.open_external_requested.connect(self.folder_open_external_requested)
            page.terminal_folder_requested.connect(self.folder_terminal_requested)
            page.rename_folder_requested.connect(self.folder_rename_requested)
            page.remove_folder_requested.connect(self.folder_remove_requested)
            page.create_script_requested.connect(self.create_script_requested)
            page.create_folder_requested.connect(self.create_folder_requested)
            page.external_files_dropped.connect(
                self.external_files_import_requested
            )
            self._folder_pages[folder_path] = page
            self.stack.addWidget(page)
        self.current_module = None; self.current_folder = folder_path
        self.stack.setCurrentWidget(page)
        self.current_folder_changed.emit(folder_path)
        return page

    def open_module(self, module_or_path) -> EditorPage | None:
        module = self._resolve_module(module_or_path)
        if module is None:
            self.status_message.emit("The selected script is no longer available.")
            return None
        state = self.states.ensure(module.path)
        page = state.editor_page
        if not isinstance(page, EditorPage):
            page = self._create_editor_page(module)
            state.editor_page = page; state.editor = page.editor; state.page_created = True
            module.loaded = True
        self.current_folder = None; self.current_module = module
        self.stack.setCurrentWidget(page); page.editor.setFocus()
        self.current_module_changed.emit(module)
        return page

    def _create_editor_page(self, module) -> EditorPage:
        page = EditorPage(module, self.repository, self.config, self.stack)
        page.status_message.connect(self.status_message)
        page.launch_requested.connect(self.launch_requested)
        page.terminal_requested.connect(self.terminal_requested)
        page.admin_terminal_requested.connect(self.admin_terminal_requested)
        page.run_with_arguments_requested.connect(self.run_with_arguments_requested)
        page.syntax_lint_requested.connect(self.syntax_lint_requested)
        page.interpreter_requested.connect(self.interpreter_requested)
        page.working_directory_requested.connect(self.working_directory_requested)
        page.environment_profiles_requested.connect(self.environment_profiles_requested)
        page.stop_requested.connect(self.stop_requested)
        page.force_stop_requested.connect(self.force_stop_requested)
        page.external_editor_requested.connect(self.external_editor_requested)
        page.containing_folder_requested.connect(
            self.containing_folder_requested
        )
        page.rename_requested.connect(self.rename_requested)
        page.executable_toggle_requested.connect(self.executable_toggle_requested)
        page.remove_requested.connect(self.remove_requested)
        page.duplicate_requested.connect(self.duplicate_requested)
        page.undo_redo_changed.connect(self.editor_history_changed)
        page.preferences_changed.connect(self.apply_editor_preferences)
        page.preferences_changed.connect(self.editor_preferences_changed)
        page.external_files_dropped.connect(self.external_files_import_requested)
        self.stack.addWidget(page)
        return page

    def apply_editor_preferences(self) -> None:
        """Apply shared Sheepy-derived editor display preferences to open pages."""
        for _path, state in tuple(self.states):
            page = state.editor_page
            if isinstance(page, EditorPage):
                page.apply_preferences()

    def close_module(self, module_or_path) -> bool:
        module = self._resolve_module(module_or_path)
        if module is None: return True
        state = self.states.get(module.path)
        if state is None or not isinstance(state.editor_page, EditorPage): return True
        page = state.editor_page
        if not page.can_close(): return False
        if self.stack.currentWidget() is page: self.show_dashboard()
        self.stack.removeWidget(page); page.deleteLater(); state.clear_editor()
        module.loaded = False; self.repository.set_dirty(module.path, False)
        return True

    def close_pages_in_folder(self, folder_path) -> bool:
        folder = Path(folder_path).expanduser().resolve(strict=False)
        targets = []
        for module in self.repository:
            try: module.path.relative_to(folder)
            except ValueError: continue
            state = self.states.get(module.path)
            if state is not None and isinstance(state.editor_page, EditorPage):
                targets.append((module, state, state.editor_page))
        for _module, _state, page in targets:
            if not page.can_close(): return False
        for module, state, page in targets:
            if self.stack.currentWidget() is page: self.show_dashboard()
            self.stack.removeWidget(page); page.deleteLater(); state.clear_editor()
            module.loaded = False; self.repository.set_dirty(module.path, False)
        return True

    def close_folder_page(self, folder_path) -> None:
        path = Path(folder_path).expanduser().resolve(strict=False)
        page = self._folder_pages.pop(path, None)
        if page is not None:
            if self.stack.currentWidget() is page: self.show_dashboard()
            self.stack.removeWidget(page); page.deleteLater()
        if self.current_folder == path: self.current_folder = None

    def can_close_application(self) -> bool:
        for module in tuple(self.repository.dirty):
            state = self.states.get(module.path)
            if state is not None and isinstance(state.editor_page, EditorPage):
                if not state.editor_page.can_close():
                    self.open_module(module); return False
        return True

    def current_path(self):
        if self.current_module is not None: return self.current_module.path
        return self.current_folder

    def set_sort_mode(self, mode): self.dashboard.set_sort_mode(mode)
    def set_search_text(self, text): self.dashboard.set_search_text(text)
    def set_view_mode(self, mode): self.dashboard.set_view_mode(mode)

    def _on_state_removed(self, module, state) -> None:
        """Dispose UI objects after a module is removed externally or internally."""
        page = state.editor_page
        if isinstance(page, QWidget):
            if self.stack.currentWidget() is page:
                self.show_dashboard()
            self.stack.removeWidget(page)
            page.deleteLater()
        state.clear_editor()
        if self.current_module is module:
            self.current_module = None

    def _on_repository_reset(self) -> None:
        self.show_dashboard()
        for _path, state in tuple(self.states):
            page = state.editor_page
            if isinstance(page, QWidget): self.stack.removeWidget(page); page.deleteLater()
            state.clear_editor()
        for page in self._folder_pages.values(): self.stack.removeWidget(page); page.deleteLater()
        self._folder_pages.clear()

    def _resolve_module(self, value):
        if isinstance(value, Module):
            return self.repository.get(value.path) or value
        return self.repository.get(value)
