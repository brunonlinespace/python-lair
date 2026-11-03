# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Main application window for Python Lair 2."""

from __future__ import annotations

import json
import os
import sys
import time
import subprocess
from pathlib import Path

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QDragEnterEvent,
    QDropEvent,
    QIcon,
    QKeySequence,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from python_lair2.app_constants import APP_WINDOW_TITLE, GITHUB_URL, ISSUES_URL
from python_lair2.controllers.editor_manager import EditorManager
from python_lair2.controllers.file_actions import FileActionsController
from python_lair2.models.module import Module
from python_lair2.models.module_repository import ModuleRepository
from python_lair2.models.module_state_store import ModuleStateStore
from python_lair2.services.config_service import ConfigService
from python_lair2.services.filesystem_watcher import FilesystemWatcher
from python_lair2.services.process_manager import ProcessManager
from python_lair2.services.runtime_launcher import RuntimeLauncher
from python_lair2.services.runtime_paths import RuntimePaths
from python_lair2.services.script_runtime import (
    format_environment_lines,
    normalise_environment_profiles,
    parse_argument_string,
    parse_environment_lines,
)
from python_lair2.widgets.about_dialog import AboutDialog
from python_lair2.widgets.closing_dialog import ClosingDialog
from python_lair2.widgets.editor_page import EditorPage
from python_lair2.widgets.navigation import (
    NavigationWidget,
    SIDEBAR_MINIMUM_WIDTH,
)
from python_lair2.widgets.preferences_dialog import PreferencesDialog
from python_lair2.widgets.shortcuts_dialog import ShortcutsDialog


SHUTDOWN_PROFILE_ENV = "PYTHON_LAIR_PROFILE_SHUTDOWN"


class MainWindow(QMainWindow):
    """Assembles the repository, services, controllers, and persistent views."""

    def __init__(
        self,
        library_root: str | Path,
        config: ConfigService,
        runtime_paths: RuntimePaths,
        parent=None,
        *,
        icon_path: str | Path | None = None,
    ) -> None:
        super().__init__(parent)
        self.library_root = Path(library_root).expanduser().resolve(strict=False)
        self.config = config
        self.runtime_paths = runtime_paths
        self.setWindowTitle(APP_WINDOW_TITLE)
        self.setAcceptDrops(True)

        self.package_root = Path(__file__).resolve().parent.parent
        self.project_root = self.package_root.parent
        self.icon_path = (
            Path(icon_path)
            if icon_path is not None
            else self.package_root / "assets" / "icons" / "python-lair-2.png"
        )
        if self.icon_path.exists():
            self.setWindowIcon(QIcon(str(self.icon_path)))

        self.repository = ModuleRepository(self)
        self.states = ModuleStateStore(self.repository, self)
        self.watcher = FilesystemWatcher(self.library_root, self.repository, parent=self)
        self.runtime_launcher = RuntimeLauncher(self.runtime_paths, self)
        self.process_manager = ProcessManager(
            self.repository,
            self.states,
            self.runtime_launcher,
            self,
        )

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.navigation = NavigationWidget(self.library_root, self.repository, self.states, self.splitter)
        self.stack = QStackedWidget(self.splitter)
        self.splitter.addWidget(self.navigation)
        self.splitter.addWidget(self.stack)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        # Easier grab target without changing either pane's contents.
        self.splitter.setHandleWidth(8)
        # Keep the validated rubber-band resize path for large Grid views:
        # one layout pass on release rather than continuous reflow.
        self.splitter.setOpaqueResize(False)
        self.setCentralWidget(self.splitter)

        self.editor_manager = EditorManager(
            self.library_root, self.repository, self.states, self.stack, self.config, self
        )
        self.file_actions = FileActionsController(
            self.library_root,
            self.repository,
            self.states,
            self.editor_manager,
            self.runtime_launcher,
            watcher=self.watcher,
            parent_widget=self,
            parent=self,
        )

        self.runtime_launcher.status_message.connect(self.show_status)
        self.runtime_launcher.launch_error.connect(self._show_launch_error)

        self._closing = False
        self.about_dialog: AboutDialog | None = None
        self._status_label = QLabel("Ready.")
        self._repair_navigation_after_scan = False
        status = QStatusBar(self)
        status.addWidget(self._status_label, 1)
        self.setStatusBar(status)

        self._build_menu_bar()
        self._connect_signals()
        self._restore_window_state()
        self.watcher.start(initial_scan=True)
        self._update_action_states()

    def _add_action(self, menu, text, slot, shortcut=None, *, checkable=False):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.setCheckable(checkable)
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    def _build_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        self.new_action = self._add_action(file_menu, "&New Script…", self._new_script, QKeySequence.StandardKey.New)
        self.new_folder_action = self._add_action(file_menu, "New &Folder…", self._new_folder, QKeySequence("Ctrl+Shift+N"))
        self.import_action = self._add_action(file_menu, "&Import Script(s)…", self._import_scripts, QKeySequence.StandardKey.Open)
        file_menu.addSeparator()
        self.new_workspace_action = self._add_action(file_menu, "New &Workspace…", self._new_workspace)
        self.open_workspace_action = self._add_action(file_menu, "Open W&orkspace…", self._open_workspace)
        file_menu.addSeparator()
        self.open_script_folder_action = self._add_action(file_menu, "Open Script's Containing &Folder", self._open_current_script_folder)
        self.open_folder_external_action = self._add_action(file_menu, "Open Current Folder E&xternally", self._open_current_folder_external)
        self.open_folder_terminal_action = self._add_action(file_menu, "Open Current Folder in &Terminal", self._open_current_folder_terminal)
        self.rename_folder_action = self._add_action(file_menu, "Rename Current F&older…", self._rename_current_folder)
        self.remove_folder_action = self._add_action(file_menu, "Remove Current Folder…", self._remove_current_folder)
        file_menu.addSeparator()
        self.save_action = self._add_action(file_menu, "&Save", self._save_current, QKeySequence.StandardKey.Save)
        self.duplicate_action = self._add_action(file_menu, "&Duplicate Current Script…", self._duplicate_current, QKeySequence("Ctrl+Shift+D"))
        self.properties_action = self._add_action(file_menu, "Script &Properties…", self._show_properties)
        file_menu.addSeparator()
        self.exit_action = self._add_action(file_menu, "E&xit", self.close, QKeySequence.StandardKey.Quit)

        edit_menu = self.menuBar().addMenu("&Edit")
        self.undo_action = self._add_action(edit_menu, "&Undo", self._undo, QKeySequence.StandardKey.Undo)
        self.redo_action = self._add_action(edit_menu, "&Redo", self._redo, QKeySequence.StandardKey.Redo)
        edit_menu.addSeparator()
        self.cut_action = self._add_action(edit_menu, "Cu&t", self._cut, QKeySequence.StandardKey.Cut)
        self.copy_action = self._add_action(edit_menu, "&Copy", self._copy, QKeySequence.StandardKey.Copy)
        self.paste_action = self._add_action(edit_menu, "&Paste", self._paste, QKeySequence.StandardKey.Paste)
        self.delete_text_action = self._add_action(edit_menu, "&Delete", self._delete_text, QKeySequence.StandardKey.Delete)
        edit_menu.addSeparator()
        self.comment_action = self._add_action(edit_menu, "Toggle &Comment", self._toggle_comment, QKeySequence("Ctrl+/"))
        self.duplicate_line_action = self._add_action(edit_menu, "Duplicate &Line or Selection", self._duplicate_line, QKeySequence("Ctrl+D"))
        self.select_all_action = self._add_action(edit_menu, "Select &All", self._select_all, QKeySequence.StandardKey.SelectAll)
        edit_menu.addSeparator()
        self.find_action = self._add_action(edit_menu, "&Find", self._focus_find, QKeySequence.StandardKey.Find)
        self.replace_action = self._add_action(edit_menu, "Find and &Replace", self._focus_replace, QKeySequence("Ctrl+H"))
        self.goto_action = self._add_action(edit_menu, "&Go to Line…", self._go_to_line, QKeySequence("Ctrl+G"))
        edit_menu.addSeparator()
        # Original Python Lair 2 Preferences entry.
        self.preferences_action = self._add_action(edit_menu, "&Preferences…", self._show_preferences)

        view_menu = self.menuBar().addMenu("&View")
        # Original Python Lair 2 View block.
        self.dashboard_action = self._add_action(
            view_menu,
            "Show &Dashboard",
            self.editor_manager.show_dashboard,
            QKeySequence("Ctrl+Alt+D"),
        )
        view_menu.addSeparator()

        view_group = QActionGroup(self)
        view_group.setExclusive(True)
        self.list_action = self._add_action(
            view_menu,
            "&List View",
            lambda: self.editor_manager.set_view_mode("list"),
            checkable=True,
        )
        self.grid_action = self._add_action(
            view_menu,
            "&Grid View",
            lambda: self.editor_manager.set_view_mode("grid"),
            checkable=True,
        )
        view_group.addAction(self.list_action)
        view_group.addAction(self.grid_action)

        view_menu.addSeparator()
        self.sidebar_action = self._add_action(
            view_menu,
            "Show &Sidebar",
            self._toggle_sidebar,
            checkable=True,
        )
        self.sidebar_action.setChecked(True)
        self.fullscreen_action = self._add_action(
            view_menu,
            "&Full Screen",
            self._toggle_fullscreen,
            QKeySequence("F11"),
            checkable=True,
        )

        # Newer Sheepy-derived view/editor controls remain available.
        view_menu.addSeparator()
        self.view_only_action = self._add_action(
            view_menu,
            "View &Only",
            self._toggle_view_only,
            checkable=True,
        )
        self.word_wrap_action = self._add_action(
            view_menu,
            "&Word Wrap",
            self._toggle_word_wrap,
            checkable=True,
        )
        self.line_numbers_action = self._add_action(
            view_menu,
            "Line &Numbers",
            self._toggle_line_numbers,
            checkable=True,
        )
        self.display_font_action = self._add_action(
            view_menu,
            "Display &Font…",
            self._choose_display_font,
        )
        self.status_bar_action = self._add_action(
            view_menu,
            "Status &Bar",
            self._toggle_status_bar,
            checkable=True,
        )
        self.status_bar_action.setChecked(bool(self.config.get("show_status_bar", True)))
        self.statusBar().setVisible(self.status_bar_action.isChecked())

        run_menu = self.menuBar().addMenu("&Run")
        self.run_action = self._add_action(run_menu, "&Run Script", self._run_current, QKeySequence("F5"))
        self.terminal_action = self._add_action(run_menu, "Run in &Terminal", self._run_terminal, QKeySequence("Ctrl+Shift+T"))
        self.admin_terminal_action = self._add_action(run_menu, "Run as &Administrator in Terminal", self._run_admin_terminal, QKeySequence("Ctrl+Alt+Shift+T"))
        self.arguments_action = self._add_action(run_menu, "Run with &Arguments…", self._run_with_arguments, QKeySequence("Ctrl+Shift+R"))
        run_menu.addSeparator()
        self.syntax_action = self._add_action(run_menu, "Syntax / &Lint Check", self._syntax_lint_check, QKeySequence("Ctrl+Shift+L"))
        self.interpreter_action = self._add_action(run_menu, "Select &Interpreter…", self._select_interpreter)
        self.working_directory_action = self._add_action(run_menu, "Working &Directory…", self._select_working_directory)
        self.environment_action = self._add_action(run_menu, "Environment &Profiles…", self._manage_environment_profiles)
        run_menu.addSeparator()
        self.stop_action = self._add_action(run_menu, "&Stop Script", self._stop_current, QKeySequence("Shift+F5"))
        self.force_stop_action = self._add_action(run_menu, "&Force Stop Script", self._force_stop_current, QKeySequence("Ctrl+Shift+F5"))
        run_menu.addSeparator()
        self.executable_action = self._add_action(run_menu, "Make &Executable", self._toggle_current_executable, QKeySequence("Ctrl+Alt+X"))

        # Complete original Python Lair 2 Help menu.
        help_menu = self.menuBar().addMenu("&Help")
        self.docs_action = self._add_action(help_menu, "&Documentation", self._open_documentation, QKeySequence.StandardKey.HelpContents)
        self.shortcuts_action = self._add_action(help_menu, "&Keyboard Shortcuts", self._show_shortcuts)
        help_menu.addSeparator()
        self.github_action = self._add_action(help_menu, "GitHub &Repository", self._open_github)
        self.issue_action = self._add_action(help_menu, "&Report an Issue", self._open_issues)
        help_menu.addSeparator()
        about_action = self._add_action(help_menu, "&About Python Lair 2", self._show_about_dialog)
        about_action.setMenuRole(QAction.MenuRole.AboutRole)

    def _current_page(self) -> EditorPage | None:
        page = self.stack.currentWidget()
        return page if isinstance(page, EditorPage) else None

    def _current_module(self) -> Module | None:
        return self.editor_manager.current_module

    def _creation_folder(self) -> Path:
        """Return the selected mini-dashboard folder, or workspace root."""
        return self._selected_folder() or self.library_root

    def _new_script(self) -> None:
        self.file_actions.create_script(self._creation_folder())

    def _new_folder(self) -> None:
        created = self.file_actions.create_folder(self._creation_folder())
        if created is not None:
            # Empty folders contain no modules, so a repository rescan alone
            # cannot add them to the script-derived tree. Rebuild the tree
            # after the directory is created so the folder appears at once.
            QTimer.singleShot(100, self.navigation.rebuild_from_repository)

    def _import_scripts(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Import Python Scripts", str(Path.home()), "Python scripts (*.py)")
        if paths:
            self.file_actions.import_files(paths)

    def _choose_workspace(self, title: str, *, create: bool) -> None:
        if create:
            parent = QFileDialog.getExistingDirectory(self, title, str(self.library_root.parent))
            if not parent:
                return
            name, accepted = QInputDialog.getText(self, title, "Workspace folder name:", text="Python Workspace")
            if not accepted or not name.strip():
                return
            selected = Path(parent) / name.strip()
            try:
                selected.mkdir(parents=True, exist_ok=False)
            except FileExistsError:
                QMessageBox.warning(self, "Workspace Exists", "That folder already exists.")
                return
            except OSError as error:
                QMessageBox.critical(self, "Workspace Error", str(error))
                return
        else:
            chosen = QFileDialog.getExistingDirectory(self, title, str(self.library_root))
            if not chosen:
                return
            selected = Path(chosen)
        self.config.set("workspace_path", str(selected.resolve()), save=True)
        QMessageBox.information(self, "Workspace Saved", "The selected workspace will open the next time Python Lair 2 starts.")

    def _new_workspace(self) -> None:
        self._choose_workspace("New Workspace", create=True)

    def _open_workspace(self) -> None:
        self._choose_workspace("Open Workspace", create=False)


    def _selected_folder(self) -> Path | None:
        return self.editor_manager.current_folder

    def _open_current_script_folder(self) -> None:
        module = self._current_module()
        if module is not None:
            self.file_actions.open_module_folder(module)

    def _open_current_folder_external(self) -> None:
        folder = self._selected_folder()
        if folder is not None:
            self.file_actions.open_folder_external(folder)

    def _open_current_folder_terminal(self) -> None:
        folder = self._selected_folder()
        if folder is not None:
            self.file_actions.open_folder_terminal(folder)

    def _rename_current_folder(self) -> None:
        folder = self._selected_folder()
        if folder is not None:
            self.file_actions.rename_folder(folder)

    def _remove_current_folder(self) -> None:
        folder = self._selected_folder()
        if folder is not None:
            self.file_actions.remove_folder(folder)

    def _save_current(self) -> None:
        page = self._current_page()
        if page:
            page.save_to_disk()

    def _undo(self) -> None:
        page = self._current_page()
        if page:
            page.editor.undo()

    def _redo(self) -> None:
        page = self._current_page()
        if page:
            page.editor.redo()

    def _cut(self) -> None:
        page = self._current_page()
        if page:
            page.editor.cut()

    def _copy(self) -> None:
        page = self._current_page()
        if page:
            page.editor.copy()

    def _delete_text(self) -> None:
        page = self._current_page()
        if page:
            page.editor.delete_selection_or_character()

    def _toggle_comment(self) -> None:
        page = self._current_page()
        if page:
            page.editor.toggle_comment()

    def _duplicate_line(self) -> None:
        page = self._current_page()
        if page:
            page.editor.duplicate_current_line_or_selection()

    def _paste(self) -> None:
        page = self._current_page()
        if page:
            page.editor.paste_safely()

    def _select_all(self) -> None:
        page = self._current_page()
        if page:
            page.editor.select_all_text()

    def _duplicate_current(self) -> None:
        module = self._current_module()
        if module is not None:
            self.file_actions.duplicate_module(module)

    def _focus_find(self) -> None:
        page = self._current_page()
        if page:
            page.find_input.setFocus()
            page.find_input.selectAll()

    def _focus_replace(self) -> None:
        page = self._current_page()
        if page:
            page.replace_input.setFocus()
            page.replace_input.selectAll()

    def _go_to_line(self) -> None:
        page = self._current_page()
        if page:
            page.show_go_to_line()

    def _show_preferences(self) -> None:
        before = self.config.get("workspace_path")
        dialog = PreferencesDialog(self.config, self.library_root, self)
        if dialog.exec() and self.config.get("workspace_path") != before:
            QMessageBox.information(self, "Restart Required", "Restart Python Lair 2 to use the new workspace folder.")

    def _show_properties(self) -> None:
        page = self._current_page()
        if page:
            page.show_properties_dialog()

    def _toggle_view_only(self, checked: bool) -> None:
        page = self._current_page()
        if not page:
            self.view_only_action.setChecked(False)
            return
        page.view_only_action.setChecked(bool(checked))
        page.toggle_view_only(bool(checked))
        self._sync_editor_view_actions()

    def _toggle_word_wrap(self, checked: bool) -> None:
        page = self._current_page()
        if page:
            page.word_wrap_action.setChecked(bool(checked))
            page.toggle_word_wrap(bool(checked))

    def _toggle_line_numbers(self, checked: bool) -> None:
        page = self._current_page()
        if page:
            page.line_numbers_action.setChecked(bool(checked))
            page.toggle_line_numbers(bool(checked))

    def _choose_display_font(self) -> None:
        page = self._current_page()
        if page:
            page.choose_display_font()

    def _sync_editor_view_actions(self) -> None:
        page = self._current_page()
        self.view_only_action.blockSignals(True)
        self.word_wrap_action.blockSignals(True)
        self.line_numbers_action.blockSignals(True)
        self.view_only_action.setChecked(bool(page and page.view_only))
        self.word_wrap_action.setChecked(bool(self.config.get("editor_word_wrap", False)))
        self.line_numbers_action.setChecked(bool(self.config.get("editor_line_numbers", True)))
        self.view_only_action.blockSignals(False)
        self.word_wrap_action.blockSignals(False)
        self.line_numbers_action.blockSignals(False)

    def _interpreter_override(self) -> str | None:
        value = str(self.config.get("interpreter_override", "") or "").strip()
        return value or None

    def _environment_profiles(self) -> dict[str, dict[str, str]]:
        return normalise_environment_profiles(self.config.get("environment_profiles"))

    def _active_environment(self, profile: str | None = None) -> dict[str, str]:
        profiles = self._environment_profiles()
        selected = profile or str(self.config.get("active_environment_profile", "Default"))
        return dict(profiles.get(selected, profiles.get("Default", {})))

    def _resolved_working_directory(self, module: Module) -> Path | None:
        if self.config.get("working_directory_mode", "script") != "custom":
            return module.path.parent
        value = str(self.config.get("custom_working_directory", "") or "").strip()
        candidate = Path(value).expanduser() if value else module.path.parent
        if candidate.is_dir():
            return candidate.resolve(strict=False)
        QMessageBox.warning(self, "Working Directory Unavailable", "The selected working directory no longer exists.")
        return None

    def _prepare_module_for_run(self, module: Module) -> bool:
        state = self.states.get(module.path)
        if state is not None and isinstance(state.editor_page, EditorPage):
            page = state.editor_page
            if page.editor.is_modified and not page.save_to_disk():
                return False
        return module.path.is_file()

    def _launch_module(
        self, module: Module, *, terminal: bool = False, elevated: bool = False,
        extra_arguments: tuple[str, ...] = (), profile: str | None = None,
        working_directory: Path | None = None,
    ) -> bool:
        if not self._prepare_module_for_run(module):
            return False
        cwd = working_directory or self._resolved_working_directory(module)
        if cwd is None:
            return False
        kwargs = dict(
            extra_arguments=extra_arguments,
            interpreter_override=self._interpreter_override(),
            working_directory=cwd,
            environment=self._active_environment(profile),
        )
        if terminal or elevated:
            return self.process_manager.launch_in_terminal(
                module.path, elevated=elevated, **kwargs
            )
        return self.process_manager.launch(module.path, **kwargs)

    def _toggle_status_bar(self, checked: bool) -> None:
        self.statusBar().setVisible(bool(checked))
        self.config.set("show_status_bar", bool(checked), save=True)
        self.editor_manager.apply_editor_preferences()

    def _toggle_sidebar(self, checked: bool) -> None:
        self.navigation.setVisible(checked)

    def _toggle_fullscreen(self, checked: bool) -> None:
        self.showFullScreen() if checked else self.showNormal()

    def _run_current(self) -> None:
        module = self._current_module()
        if module:
            self._launch_module(module)

    def _run_terminal(self) -> None:
        module = self._current_module()
        if module:
            self._launch_module(module, terminal=True)

    def _run_admin_terminal(self) -> None:
        module = self._current_module()
        if module is None:
            return
        if self.process_manager.is_running(module.path):
            QMessageBox.information(
                self,
                "Script Running",
                "This script is already running.",
            )
            return
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("Run as Administrator?")
        dialog.setText(
            f"Run {module.filename} with administrator privileges?"
        )
        dialog.setInformativeText(
            "The script could modify or delete system files. A terminal will "
            "open and sudo will request authentication when required; Python "
            "Lair never reads or stores credentials. Elevated runs are not "
            "supervised, so Stop and Force Stop will not control this process."
        )
        cancel_button = dialog.addButton(
            "Cancel", QMessageBox.ButtonRole.RejectRole
        )
        continue_button = dialog.addButton(
            "Continue", QMessageBox.ButtonRole.AcceptRole
        )
        dialog.setDefaultButton(cancel_button)
        dialog.setEscapeButton(cancel_button)
        dialog.exec()
        if dialog.clickedButton() is not continue_button:
            self.show_status("Administrator launch cancelled.")
            return
        self._launch_module(module, terminal=True, elevated=True)

    def _run_with_arguments(self) -> None:
        module = self._current_module()
        if module is None:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Run with Arguments")
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        arguments = QLineEdit(str(self.config.get("last_run_arguments", "") or ""))
        arguments.setPlaceholderText('--option value "argument with spaces"')
        form.addRow("Arguments:", arguments)
        profiles = self._environment_profiles()
        profile_combo = QComboBox(dialog)
        profile_combo.addItems(sorted(profiles, key=str.casefold))
        active = str(self.config.get("active_environment_profile", "Default"))
        idx = profile_combo.findText(active)
        if idx >= 0:
            profile_combo.setCurrentIndex(idx)
        form.addRow("Environment profile:", profile_combo)
        working = QLineEdit(str(self._resolved_working_directory(module) or module.path.parent))
        browse = QPushButton("Browse…")
        working_host = QWidget(dialog); working_layout = QHBoxLayout(working_host); working_layout.setContentsMargins(0,0,0,0)
        working_layout.addWidget(working,1); working_layout.addWidget(browse)
        form.addRow("Working directory:", working_host)
        resolved = self.runtime_launcher.resolve_interpreter(module.path, self._interpreter_override())
        form.addRow("Interpreter:", QLabel(f"{resolved[0]} ({resolved[2]})" if resolved else "Not available"))
        layout.addLayout(form)
        terminal = QCheckBox("Run in terminal")
        terminal.setChecked(bool(self.config.get("last_run_in_terminal", False)))
        layout.addWidget(terminal)
        browse.clicked.connect(lambda: (lambda selected: working.setText(selected) if selected else None)(QFileDialog.getExistingDirectory(dialog, "Choose Working Directory", working.text() or str(module.path.parent))))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, dialog)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            parsed = parse_argument_string(arguments.text())
        except ValueError as error:
            QMessageBox.warning(self, "Invalid Arguments", str(error)); return
        cwd = Path(working.text()).expanduser()
        if not cwd.is_dir():
            QMessageBox.warning(self, "Invalid Working Directory", "Choose an existing working directory."); return
        profile = profile_combo.currentText() or "Default"
        self.config.update({"last_run_arguments": arguments.text(), "last_run_in_terminal": terminal.isChecked(), "active_environment_profile": profile}, save=True)
        self._launch_module(module, terminal=terminal.isChecked(), extra_arguments=parsed, profile=profile, working_directory=cwd.resolve(strict=False))

    def _syntax_lint_check(self) -> None:
        module = self._current_module()
        if module is None or not self._prepare_module_for_run(module):
            return
        resolved = self.runtime_launcher.resolve_interpreter(module.path, self._interpreter_override())
        if resolved is None:
            self._show_launch_error("No suitable Python interpreter was found."); return
        program, _prefix, source = resolved
        cwd = self._resolved_working_directory(module)
        if cwd is None:
            return
        environment = self.runtime_launcher.subprocess_environment(self._active_environment())
        compile_code = "import sys,tokenize; f=tokenize.open(sys.argv[1]); s=f.read(); f.close(); compile(s,sys.argv[1],'exec')"
        try:
            result = subprocess.run([program, "-c", compile_code, str(module.path)], cwd=cwd, env=environment, capture_output=True, text=True, errors="replace", timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            QMessageBox.critical(self, "Syntax Check Failed", str(error)); return
        output = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            QMessageBox.warning(self, "Syntax Check", (output or "Python reported a syntax error.")[:20000]); return
        ruff = self.runtime_launcher.find_host_executable("ruff")
        if not ruff:
            QMessageBox.information(self, "Syntax / Lint Check", f"Syntax OK using {program} ({source}).\n\nRuff was not found; syntax check passed."); return
        try:
            lint = subprocess.run([ruff, "check", "--no-cache", str(module.path)], cwd=cwd, env=environment, capture_output=True, text=True, errors="replace", timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            QMessageBox.warning(self, "Lint Check", f"Syntax OK, but Ruff could not complete: {error}"); return
        lint_output = (lint.stdout + lint.stderr).strip()
        if lint.returncode == 0:
            QMessageBox.information(self, "Syntax / Lint Check", "Syntax OK. Ruff reported no issues.")
        else:
            QMessageBox.warning(self, "Ruff Check", lint_output[:20000] or "Ruff reported issues.")

    def _select_interpreter(self) -> None:
        module = self._current_module()
        if module is None:
            return
        current = str(self.config.get("interpreter_override", "") or "")
        shebang = self.runtime_launcher.detected_shebang(module.path)
        resolved = self.runtime_launcher.resolve_interpreter(module.path, current or None)
        choices = ["Automatic (shebang / Python)"]
        for candidate in (self.runtime_launcher.python_executable(), "python3", "python"):
            if candidate:
                found = self.runtime_launcher.find_host_executable(candidate)
                if found and found not in choices:
                    choices.append(found)
        if current and current not in choices:
            choices.append(current)
        choices.append("Choose executable…")
        selected, accepted = QInputDialog.getItem(self, "Select Interpreter", f"Current: {resolved[0] if resolved else 'Not found'}\nShebang: {shebang or 'None'}", choices, choices.index(current) if current in choices else 0, False)
        if not accepted:
            return
        if selected == "Automatic (shebang / Python)":
            value = ""
        elif selected == "Choose executable…":
            chosen, _ = QFileDialog.getOpenFileName(self, "Choose Interpreter", current or str(Path.home()), "Executable Files (*)")
            if not chosen:
                return
            found = self.runtime_launcher.find_host_executable(chosen)
            if not found:
                QMessageBox.warning(self, "Invalid Interpreter", "The selected file is not executable."); return
            value = found
        else:
            value = selected
        self.config.set("interpreter_override", value, save=True)
        self.show_status("Interpreter selection updated.")

    def _select_working_directory(self) -> None:
        module = self._current_module()
        if module is None:
            return
        use_script = QMessageBox.question(self, "Working Directory", "Use the script's containing folder as the working directory?\n\nChoose No to select a custom directory.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Yes)
        if use_script == QMessageBox.StandardButton.Cancel:
            return
        if use_script == QMessageBox.StandardButton.Yes:
            self.config.update({"working_directory_mode": "script", "custom_working_directory": ""}, save=True)
        else:
            selected = QFileDialog.getExistingDirectory(self, "Choose Working Directory", str(self._resolved_working_directory(module) or module.path.parent))
            if not selected:
                return
            self.config.update({"working_directory_mode": "custom", "custom_working_directory": selected}, save=True)
        self.show_status("Working directory updated.")

    def _manage_environment_profiles(self) -> None:
        dialog = QDialog(self); dialog.setWindowTitle("Environment Profiles"); dialog.setMinimumSize(640, 460)
        layout = QVBoxLayout(dialog)
        intro = QLabel("Profiles add environment variables to script launches. Use one NAME=value entry per line. Do not store secrets here; values are saved as plain text."); intro.setWordWrap(True); layout.addWidget(intro)
        profiles = self._environment_profiles(); active = str(self.config.get("active_environment_profile", "Default"))
        top = QHBoxLayout(); combo = QComboBox(); top.addWidget(combo,1); new_button = QPushButton("New"); rename_button = QPushButton("Rename"); delete_button = QPushButton("Delete"); active_button = QPushButton("Set Active")
        for button in (new_button, rename_button, delete_button, active_button): top.addWidget(button)
        layout.addLayout(top); active_label = QLabel(); layout.addWidget(active_label); editor = QTextEdit(); editor.setAcceptRichText(False); layout.addWidget(editor,1)
        save_button = QPushButton("Save Profile"); close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close); bottom=QHBoxLayout(); bottom.addWidget(save_button); bottom.addStretch(1); bottom.addWidget(close_buttons); layout.addLayout(bottom)
        loading=False
        def load_current():
            if loading: return
            name=combo.currentText(); editor.setPlainText(format_environment_lines(profiles.get(name, {}))); delete_button.setEnabled(name != "Default"); active_label.setText(f"Active profile: {active}")
        def populate(target=None):
            nonlocal loading
            loading=True; combo.clear(); combo.addItems(sorted(profiles, key=lambda n:(n!="Default", n.casefold()))); loading=False
            idx=combo.findText(target if target in profiles else active); combo.setCurrentIndex(max(0,idx)); load_current()
        def save_profile():
            name=combo.currentText()
            try: profiles[name]=parse_environment_lines(editor.toPlainText())
            except ValueError as error: QMessageBox.warning(dialog,"Invalid Environment",str(error)); return
            self.config.set("environment_profiles", profiles, save=True); self.show_status(f"Saved environment profile: {name}")
        def new_profile():
            name,ok=QInputDialog.getText(dialog,"New Profile","Profile name:")
            name=name.strip()
            if ok and name and name not in profiles: profiles[name]={}; populate(name)
        def rename_profile():
            nonlocal active
            old=combo.currentText()
            if old=="Default": return
            name,ok=QInputDialog.getText(dialog,"Rename Profile","Profile name:",text=old); name=name.strip()
            if ok and name and name not in profiles: profiles[name]=profiles.pop(old); active=name if active==old else active; self.config.update({"environment_profiles":profiles,"active_environment_profile":active},save=True); populate(name)
        def delete_profile():
            nonlocal active
            name=combo.currentText()
            if name=="Default": return
            profiles.pop(name,None); active="Default" if active==name else active; self.config.update({"environment_profiles":profiles,"active_environment_profile":active},save=True); populate(active)
        def set_active():
            nonlocal active
            active=combo.currentText() or "Default"; self.config.set("active_environment_profile",active,save=True); active_label.setText(f"Active profile: {active}")
        combo.currentTextChanged.connect(lambda _t: load_current()); save_button.clicked.connect(save_profile); new_button.clicked.connect(new_profile); rename_button.clicked.connect(rename_profile); delete_button.clicked.connect(delete_profile); active_button.clicked.connect(set_active); close_buttons.rejected.connect(dialog.reject); populate(); dialog.exec()

    def _stop_current(self) -> None:
        module = self._current_module()
        if module:
            self.process_manager.stop(module.path)

    def _force_stop_current(self) -> None:
        module = self._current_module()
        if module:
            self.process_manager.force_stop(module.path)

    def _toggle_current_executable(self) -> None:
        module = self._current_module()
        if module:
            self.file_actions.toggle_executable(module)

    def _open_documentation(self) -> None:
        readme = self.runtime_paths.package_root / "docs" / "README.md"
        if readme.exists():
            self.runtime_launcher.open_path(readme)

    def _show_shortcuts(self) -> None:
        ShortcutsDialog(self).exec()


    def _open_github(self) -> None:
        self.runtime_launcher.open_url(GITHUB_URL)

    def _open_issues(self) -> None:
        self.runtime_launcher.open_url(ISSUES_URL)

    def _show_about_dialog(self) -> None:
        if self.about_dialog is not None:
            self.about_dialog.show()
            self.about_dialog.raise_()
            self.about_dialog.activateWindow()
            return

        dialog = AboutDialog(
            self.icon_path,
            self.runtime_paths.config_path,
            self,
            runtime_launcher=self.runtime_launcher,
        )
        dialog.finished.connect(
            lambda _result: setattr(self, "about_dialog", None)
        )
        self.about_dialog = dialog
        dialog.show()

    def _connect_signals(self) -> None:
        self.navigation.dashboard_requested.connect(self.editor_manager.show_dashboard)
        self.navigation.folder_requested.connect(self.editor_manager.open_folder)
        self.navigation.module_requested.connect(self.editor_manager.open_module)
        self.navigation.module_move_requested.connect(self.file_actions.move_module)
        self.navigation.external_files_import_requested.connect(
            self.file_actions.import_files
        )
        self.editor_manager.dashboard_shown.connect(self.navigation.select_dashboard)
        self.editor_manager.dashboard_shown.connect(self._update_action_states)
        self.editor_manager.dashboard_shown.connect(self._sync_editor_view_actions)
        self.editor_manager.current_folder_changed.connect(self.navigation.select_folder)
        self.editor_manager.current_folder_changed.connect(self._update_action_states)
        self.editor_manager.current_module_changed.connect(lambda module: self.navigation.select_module(module.path))
        self.editor_manager.current_module_changed.connect(self._update_action_states)
        self.editor_manager.current_module_changed.connect(lambda _module: self._sync_editor_view_actions())
        self.editor_manager.launch_requested.connect(lambda module: self._launch_module(module))
        self.editor_manager.terminal_requested.connect(lambda module: self._launch_module(module, terminal=True))
        self.editor_manager.admin_terminal_requested.connect(
            lambda module: (
                self.editor_manager.open_module(module),
                self._run_admin_terminal(),
            )
        )
        self.editor_manager.run_with_arguments_requested.connect(lambda module: (self.editor_manager.open_module(module), self._run_with_arguments()))
        self.editor_manager.syntax_lint_requested.connect(lambda module: (self.editor_manager.open_module(module), self._syntax_lint_check()))
        self.editor_manager.interpreter_requested.connect(lambda module: (self.editor_manager.open_module(module), self._select_interpreter()))
        self.editor_manager.working_directory_requested.connect(lambda module: (self.editor_manager.open_module(module), self._select_working_directory()))
        self.editor_manager.environment_profiles_requested.connect(lambda module: (self.editor_manager.open_module(module), self._manage_environment_profiles()))
        self.editor_manager.stop_requested.connect(lambda module: self.process_manager.stop(module.path))
        self.editor_manager.force_stop_requested.connect(lambda module: self.process_manager.force_stop(module.path))
        self.editor_manager.external_editor_requested.connect(
            self.file_actions.open_external_editor
        )
        self.editor_manager.containing_folder_requested.connect(
            self.file_actions.open_module_folder
        )
        self.editor_manager.rename_requested.connect(self.file_actions.rename_module)
        self.editor_manager.executable_toggle_requested.connect(self.file_actions.toggle_executable)
        self.editor_manager.remove_requested.connect(self.file_actions.remove_module)
        self.editor_manager.duplicate_requested.connect(
            self.file_actions.duplicate_module
        )
        self.editor_manager.editor_history_changed.connect(
            self._on_editor_history_changed
        )
        self.editor_manager.editor_preferences_changed.connect(
            self._sync_editor_view_actions
        )
        self.editor_manager.folder_open_external_requested.connect(self.file_actions.open_folder_external)
        self.editor_manager.folder_terminal_requested.connect(self.file_actions.open_folder_terminal)
        self.editor_manager.folder_rename_requested.connect(self.file_actions.rename_folder)
        self.editor_manager.folder_remove_requested.connect(self.file_actions.remove_folder)
        self.editor_manager.create_script_requested.connect(self.file_actions.create_script)
        self.editor_manager.create_folder_requested.connect(self._create_folder_from_dashboard)
        self.editor_manager.external_files_import_requested.connect(
            self.file_actions.import_files
        )
        self.editor_manager.refresh_requested.connect(self._refresh_workspace)
        self.editor_manager.sort_mode_changed.connect(self._remember_sort_mode)
        self.editor_manager.view_mode_changed.connect(self._remember_view_mode)
        self.editor_manager.view_mode_changed.connect(self._sync_view_actions)
        self.file_actions.folder_renamed.connect(self._on_folder_renamed)
        self.file_actions.folder_removed.connect(lambda _path: self.editor_manager.show_dashboard())
        for source in (self.editor_manager, self.file_actions, self.process_manager):
            source.status_message.connect(self.show_status)
        self.watcher.scan_started.connect(self._on_scan_started)
        self.watcher.folders_discovered.connect(
            self.navigation.set_disk_folders
        )
        self.watcher.scan_details.connect(self._on_scan_details)
        self.watcher.scan_finished.connect(self._on_scan_finished)
        self.watcher.scan_failed.connect(self._on_scan_failed)
        self.repository.dirty_count_changed.connect(self._update_dirty_status)
        self.repository.module_changed.connect(lambda _module: self._update_action_states())
        self.repository.module_path_changed.connect(lambda _module, _old: self._update_action_states())

    def _create_folder_from_dashboard(self, parent: Path) -> None:
        created = self.file_actions.create_folder(parent)
        if created is not None:
            QTimer.singleShot(100, self.navigation.rebuild_from_repository)

    def _sync_view_actions(self, mode: str) -> None:
        self.list_action.setChecked(mode == "list")
        self.grid_action.setChecked(mode == "grid")

    def _on_editor_history_changed(
        self,
        undo_available: bool,
        redo_available: bool,
    ) -> None:
        if self._current_page() is None:
            return
        self.undo_action.setEnabled(undo_available)
        self.redo_action.setEnabled(redo_available)

    def _update_action_states(self, *_args) -> None:
        page = self._current_page()
        module = self._current_module()
        editing = page is not None and module is not None
        for action in (
            self.save_action,
            self.undo_action,
            self.redo_action,
            self.cut_action, self.copy_action, self.paste_action, self.delete_text_action,
            self.comment_action, self.duplicate_line_action, self.select_all_action,
            self.duplicate_action, self.properties_action, self.find_action,
            self.replace_action, self.goto_action, self.view_only_action,
            self.word_wrap_action, self.line_numbers_action, self.display_font_action,
            self.run_action, self.terminal_action, self.admin_terminal_action,
            self.arguments_action, self.syntax_action, self.interpreter_action,
            self.working_directory_action, self.environment_action,
            self.executable_action, self.open_script_folder_action,
        ):
            action.setEnabled(editing)
        running = bool(module and self.process_manager.is_running(module.path))
        self.stop_action.setEnabled(running)
        self.force_stop_action.setEnabled(running)
        self.executable_action.setText(
            "Remove Executable Permission" if module and module.executable else "Make Executable"
        )
        self._sync_editor_view_actions()
        folder = self._selected_folder()
        folder_selected = folder is not None
        for action in (self.open_folder_external_action, self.open_folder_terminal_action, self.rename_folder_action, self.remove_folder_action):
            action.setEnabled(folder_selected)
        if folder_selected and folder == self.library_root:
            self.rename_folder_action.setEnabled(False)
            self.remove_folder_action.setEnabled(False)
        if page:
            view_only = page.view_only
            self.undo_action.setEnabled(page.editor.document().isUndoAvailable() and not view_only)
            self.redo_action.setEnabled(page.editor.document().isRedoAvailable() and not view_only)
            for action in (
                self.cut_action, self.paste_action, self.delete_text_action,
                self.comment_action, self.duplicate_line_action,
            ):
                action.setEnabled(not view_only)

    def _on_folder_renamed(self, old_path: Path, new_path: Path) -> None:
        self.show_status(f"Folder renamed to {new_path.name}")
        QTimer.singleShot(600, lambda: self.editor_manager.open_folder(new_path))

    def _restore_window_state(self) -> None:
        width = self.config.get_int("window_width", 1350, minimum=900)
        height = self.config.get_int("window_height", 850, minimum=600)
        self.resize(width, height)
        sizes = self.config.get_int_list(
            "splitter_sizes",
            [260, 1090],
            length=2,
        )
        self._restored_sidebar_width = (
            int(sizes[0]) if sizes and int(sizes[0]) > 0 else 260
        )
        # Restore after Qt has a real central-widget geometry. This avoids
        # stale total widths producing a jumpy or apparently stuck handle.
        QTimer.singleShot(0, self._restore_splitter_geometry)

        folders = self.config.get("collapsed_folders", [])
        if isinstance(folders, list):
            self.navigation.restore_collapsed_folders(folders)
        sort_mode = str(self.config.get("dashboard_sort", "modified"))
        search_text = str(self.config.get("dashboard_search", ""))
        view_mode = str(self.config.get("dashboard_view", "list"))
        self.editor_manager.set_sort_mode(sort_mode)
        self.editor_manager.set_search_text(search_text)
        self.editor_manager.set_view_mode(view_mode)
        self._sync_view_actions(view_mode)
        if bool(self.config.get("window_maximized", False)):
            self.showMaximized()

    def _restore_splitter_geometry(self) -> None:
        """Restore sidebar width against the live splitter geometry."""
        total_width = max(
            1,
            self.splitter.width() - max(1, self.splitter.handleWidth()),
        )

        # Keep a usable content pane even if an old saved splitter width came
        # from a very different window size.
        content_floor = min(
            420,
            max(1, total_width - SIDEBAR_MINIMUM_WIDTH),
        )
        max_sidebar = max(
            SIDEBAR_MINIMUM_WIDTH,
            total_width - content_floor,
        )

        desired = int(getattr(self, "_restored_sidebar_width", 260))
        sidebar_width = max(
            SIDEBAR_MINIMUM_WIDTH,
            min(desired, max_sidebar),
        )
        self.splitter.setSizes(
            [sidebar_width, max(1, total_width - sidebar_width)]
        )

    def _refresh_workspace(self) -> None:
        """Run one background scan, then repair navigation from its result."""
        self._repair_navigation_after_scan = True
        self.show_status("Refreshing workspace in background…")
        self.watcher.request_rescan()

    def _on_scan_started(self) -> None:
        message = (
            "Refreshing your workspace…"
            if self._repair_navigation_after_scan
            else "Preparing your workspace…"
        )
        self.editor_manager.dashboard.set_loading(True, message)
        self.navigation.set_loading(True, "Building folder tree…")
        self.show_status("Scanning workspace in background…")

    def _on_scan_details(self, entries: int, seconds: float) -> None:
        detail = f"Scanned {entries:,} filesystem entries in {seconds:.1f}s."
        self.editor_manager.dashboard.set_loading_detail(detail)
        self.navigation.set_loading_detail(
            f"{len(self.repository):,} Python scripts found"
        )
        self.show_status(detail)

    def _on_scan_finished(self, count: int) -> None:
        self.editor_manager.dashboard.set_loading(False)
        self.navigation.set_loading(False)
        if self._repair_navigation_after_scan:
            self._repair_navigation_after_scan = False
            self.navigation.rebuild_from_repository()
            self.show_status(f"Refreshed {count} script(s).")
        else:
            self.show_status(f"Loaded {count} script(s).")
        last_path = self.config.get("last_opened_script")
        if last_path:
            module = self.repository.get(last_path)
            if module is not None:
                self.editor_manager.open_module(module)
                self.config.set("last_opened_script", None)
                return
        last_folder = self.config.get("last_opened_folder")
        if last_folder and Path(last_folder).is_dir():
            self.editor_manager.open_folder(last_folder)
            self.config.set("last_opened_folder", None)

    def _on_scan_failed(self, message: str) -> None:
        self.editor_manager.dashboard.set_loading(False)
        self.navigation.set_loading(False)
        self.show_status(f"Library scan failed: {message}")
        QMessageBox.warning(self, "Library Scan Failed", message)

    def _remember_sort_mode(self, mode: str) -> None:
        self.config.set("dashboard_sort", mode)

    def _remember_view_mode(self, mode: str) -> None:
        self.config.set("dashboard_view", mode)

    def _update_dirty_status(self, count: int) -> None:
        if count:
            self.show_status(f"{count} script(s) have unsaved changes.")

    def _show_launch_error(self, message: str) -> None:
        QMessageBox.warning(self, "Launch Failed", message)

    def show_status(self, message: str) -> None:
        self._status_label.setText(message)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        if any(url.isLocalFile() and url.toLocalFile().casefold().endswith(".py") for url in urls):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile() and url.toLocalFile().casefold().endswith(".py")]
        if paths:
            self.file_actions.import_files(paths, self.library_root)
            event.acceptProposedAction()
        else:
            event.ignore()

    def _write_shutdown_timing(self, timings: dict[str, float]) -> None:
        """Write shutdown diagnostics only when explicitly requested."""
        enabled = os.environ.get(SHUTDOWN_PROFILE_ENV, "").casefold()
        if enabled not in {"1", "true", "yes", "on"}:
            return

        report_path = self.runtime_paths.config_root / "shutdown-timing.jsonl"
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "scripts": len(self.repository),
            "running": len(self.repository.running),
            "timings_ms": {
                key: round(value * 1000.0, 2)
                for key, value in timings.items()
            },
        }
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with report_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, sort_keys=True) + "\n")
        except OSError:
            pass

        printable = " · ".join(
            f"{key}={value * 1000.0:.1f} ms"
            for key, value in timings.items()
        )
        print(f"Python Lair shutdown: {printable}", flush=True)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._closing:
            event.accept()
            return

        started = time.perf_counter()
        timings: dict[str, float] = {}

        unsaved_started = time.perf_counter()
        if not self.editor_manager.can_close_application():
            timings["unsaved_prompt"] = time.perf_counter() - unsaved_started
            event.ignore()
            return
        timings["unsaved_prompt"] = time.perf_counter() - unsaved_started

        self._closing = True

        closing_dialog = ClosingDialog(self)
        closing_dialog.start()
        QApplication.processEvents()

        def stage(detail: str) -> None:
            closing_dialog.set_stage(detail)
            QApplication.processEvents()

        stage("Saving your preferences…")
        config_started = time.perf_counter()
        self.config.update(
            {
                "window_width": self.width(),
                "window_height": self.height(),
                "window_maximized": self.isMaximized(),
                "splitter_sizes": self.splitter.sizes(),
                "collapsed_folders": sorted(
                    self.navigation.collapsed_folders()
                ),
                "dashboard_sort": self.editor_manager.dashboard._sort_mode,
                "dashboard_search": (
                    self.editor_manager.dashboard.search_input.text()
                ),
                "dashboard_view": (
                    self.editor_manager.dashboard.view_mode()
                ),
                "last_opened_script": (
                    str(self.editor_manager.current_module.path)
                    if self.editor_manager.current_module is not None
                    else None
                ),
                "last_opened_folder": (
                    str(self.editor_manager.current_folder)
                    if self.editor_manager.current_folder is not None
                    else None
                ),
            },
            save=True,
        )
        timings["save_config"] = time.perf_counter() - config_started

        # Hide the large main hierarchy while retaining the small dialog.
        self.editor_manager.dashboard.set_loading(False)
        self.navigation.set_loading(False)
        self.centralWidget().hide()
        self.menuBar().hide()
        self.statusBar().hide()
        closing_dialog.adjustSize()
        closing_dialog.move(
            self.frameGeometry().center()
            - closing_dialog.rect().center()
        )
        QApplication.processEvents()

        stage("Stopping the workspace scanner…")
        scanner_started = time.perf_counter()
        scan_stopped = self.watcher.stop(
            timeout_ms=2000,
            pump_events=QApplication.processEvents,
        )
        timings["stop_scanner"] = time.perf_counter() - scanner_started

        stage("Stopping running scripts…")
        process_started = time.perf_counter()
        self.process_manager.shutdown(
            timeout_ms=1500,
            pump_events=QApplication.processEvents,
        )
        timings["stop_processes"] = time.perf_counter() - process_started

        if not scan_stopped:
            self._closing = False
            closing_dialog.close()
            self.centralWidget().show()
            self.menuBar().show()
            self.statusBar().show()
            self.show_status("Could not cancel the workspace scan yet.")
            event.ignore()
            return

        timings["total_before_exit"] = time.perf_counter() - started
        self._write_shutdown_timing(timings)

        stage("Closing Python Lair…")
        event.accept()
        QApplication.processEvents()

        try:
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            os._exit(0)
