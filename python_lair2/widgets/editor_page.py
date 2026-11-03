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
widgets/editor_page.py

One lazily-created editor page for a Module.

Responsibilities:
- load and save a single file
- synchronize Qt's native modified flag with ModuleRepository
- provide Find, Replace, and Go to Line controls
- detect external file changes without silently discarding edits
- expose launch, terminal, external-editor, rename, permission, and remove signals

The page does not launch processes or rename/delete files itself. Those actions
belong to controllers and services, keeping this widget focused and testable.
"""

from __future__ import annotations

from html import escape
import codecs
import io
import locale
import os
from pathlib import Path
import tempfile
import tokenize

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QFontDatabase, QTextCursor, QTextDocument, QKeySequence
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFontDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from python_lair2.models.module import Module
from python_lair2.models.module_repository import ModuleRepository
from python_lair2.widgets.code_editor import CodeEditor
from python_lair2.services.config_service import ConfigService
from python_lair2.services.file_io import (
    FileSnapshot,
    FileStateChangedError,
    FileTooLargeError,
    UnsupportedFileError,
    current_file_state,
    fsync_directory,
    install_new_file_from_temp,
    read_regular_file,
    snapshot_from_payload,
    validated_symlink_target,
)


class EditorPage(QWidget):
    """Editor and file controls for one repository Module."""

    MAX_FILE_BYTES = 25 * 1024 * 1024
    MAX_SEARCH_QUERY_CHARACTERS = 4096
    MAX_SEARCH_MATCHES = 10_000

    launch_requested = pyqtSignal(object)
    terminal_requested = pyqtSignal(object)
    admin_terminal_requested = pyqtSignal(object)
    run_with_arguments_requested = pyqtSignal(object)
    syntax_lint_requested = pyqtSignal(object)
    interpreter_requested = pyqtSignal(object)
    working_directory_requested = pyqtSignal(object)
    environment_profiles_requested = pyqtSignal(object)
    stop_requested = pyqtSignal(object)
    force_stop_requested = pyqtSignal(object)
    external_editor_requested = pyqtSignal(object)
    containing_folder_requested = pyqtSignal(object)
    rename_requested = pyqtSignal(object)
    executable_toggle_requested = pyqtSignal(object)
    remove_requested = pyqtSignal(object)
    duplicate_requested = pyqtSignal(object)
    undo_redo_changed = pyqtSignal(bool, bool)
    status_message = pyqtSignal(str)
    saved = pyqtSignal(object)
    preferences_changed = pyqtSignal()
    external_files_dropped = pyqtSignal(object, object)

    def __init__(
        self,
        module: Module,
        repository: ModuleRepository,
        config: ConfigService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.module = module
        self.repository = repository
        self.config = config
        self.editor = CodeEditor(self)
        self.view_only = False
        self._view_only_notice_shown = False
        self.file_encoding = "utf-8"
        self.file_bom = b""
        self.file_newline = "\n"
        self.file_disk_snapshot: FileSnapshot | None = None

        self._loaded_mtime_ns: int | None = None
        self._external_change_pending = False
        self._ignore_document_signal = False
        self._last_find_text = ""
        self._search_matches: list[tuple[int, int]] = []
        self._current_search_index = -1
        self._search_results_truncated = False

        self._build_ui()
        self._connect_signals()
        self.load_from_disk(show_errors=False)
        self._refresh_header()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        self.title_label = QLabel()
        self.title_label.setWordWrap(True)
        root.addWidget(self.title_label)

        self.external_banner = QFrame()
        self.external_banner.setFrameShape(QFrame.Shape.StyledPanel)
        banner_layout = QHBoxLayout(self.external_banner)
        self.external_label = QLabel("This file changed on disk after it was opened.")
        self.external_label.setWordWrap(True)
        banner_layout.addWidget(self.external_label, 1)
        reload_external = QPushButton("Reload from Disk")
        reload_external.clicked.connect(self._reload_external_change)
        keep_editor = QPushButton("Keep My Version")
        keep_editor.clicked.connect(self._keep_editor_version)
        banner_layout.addWidget(reload_external)
        banner_layout.addWidget(keep_editor)
        self.external_banner.hide()
        root.addWidget(self.external_banner)

        # Keep the Sheepy-derived editor actions internally available for
        # state synchronization; the application-global menu bar is the only
        # visible editor command menu surface.
        self._build_editor_menus()

        # Direct editor actions restored from the original Python Lair,
        # legacy layout, and Sheepy Pad's compact run controls. These are
        # native text-only QPushButtons and deliberately reuse the same
        # signals/methods as the embedded menus.
        editor_action_row = QHBoxLayout()
        editor_action_row.setContentsMargins(0, 0, 0, 0)
        editor_action_row.setSpacing(6)
        editor_action_row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.launch_button = QPushButton("Launch")
        self.terminal_button = QPushButton("In Terminal")
        self.admin_button = QPushButton("As Admin")
        self.stop_button = QPushButton("Stop")
        self.force_stop_button = QPushButton("Force Stop")
        self.executable_button = QPushButton("Make Exec")
        self.cancel_changes_button = QPushButton("Cancel Changes")
        self.save_changes_button = QPushButton("Save Changes")

        editor_action_row.addWidget(self.launch_button)
        editor_action_row.addWidget(self.terminal_button)
        editor_action_row.addWidget(self.admin_button)
        editor_action_row.addWidget(self.stop_button)
        editor_action_row.addWidget(self.force_stop_button)
        editor_action_row.addWidget(self.executable_button)

        self.editor_action_separator = QFrame()
        self.editor_action_separator.setFrameShape(QFrame.Shape.VLine)
        self.editor_action_separator.setFrameShadow(QFrame.Shadow.Sunken)
        editor_action_row.addWidget(self.editor_action_separator)

        editor_action_row.addWidget(self.cancel_changes_button)
        editor_action_row.addWidget(self.save_changes_button)
        editor_action_row.addStretch(1)
        root.addLayout(editor_action_row)

        root.addWidget(self.editor, 1)

        search_row = QHBoxLayout()
        self.find_input = QLineEdit()
        self.find_input.setMaxLength(self.MAX_SEARCH_QUERY_CHARACTERS)
        self.find_input.setPlaceholderText("Find text…")
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace with…")
        self.case_sensitive = QCheckBox("Match case")
        self.search_counter = QLabel("0/0")
        self.search_counter.setMinimumWidth(52)
        self.search_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        search_row.addWidget(self.find_input, 1)
        search_row.addWidget(self.search_counter)
        search_row.addWidget(self.replace_input, 1)
        search_row.addWidget(self.case_sensitive)
        root.addLayout(search_row)

        self.editor_status = QStatusBar(self)
        self.position_label = QLabel("Ln 1/1, Col 1, Char 0")
        self.operation_mode_label = QLabel("Insert")
        self.executable_status_label = QLabel("Exec: No")
        self.encoding_status_label = QLabel("UTF-8")
        # Sheepy-derived compact status order: edit mode, executable state,
        # cursor/document position, then encoding.
        self.editor_status.addWidget(self.operation_mode_label)
        self.editor_status.addWidget(self.executable_status_label)
        self.editor_status.addWidget(self.position_label, 1)
        self.editor_status.addPermanentWidget(self.encoding_status_label)
        root.addWidget(self.editor_status)

        self.apply_preferences()

    def _menu_action(
        self, menu, text: str, callback, *, checkable: bool = False,
        shortcut: str | None = None,
    ) -> QAction:
        action = QAction(text, self)
        action.setCheckable(checkable)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
            action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        action.triggered.connect(callback)
        menu.addAction(action)
        return action

    def _build_editor_menus(self) -> None:
        self.editor_file_menu = QMenu("File", self)
        file_menu = self.editor_file_menu
        self.save_action = self._menu_action(file_menu, "Save Changes", self.save_to_disk)
        self.discard_action = self._menu_action(file_menu, "Discard Changes", self.confirm_reload)
        file_menu.addSeparator()
        self.properties_action = self._menu_action(file_menu, "Properties…", self.show_properties_dialog)
        file_menu.addSeparator()
        self.external_action = self._menu_action(file_menu, "Open in External Editor", lambda: self.external_editor_requested.emit(self.module))
        self.folder_action = self._menu_action(file_menu, "Open Containing Folder", lambda: self.containing_folder_requested.emit(self.module))
        self.rename_action = self._menu_action(file_menu, "Rename…", lambda: self.rename_requested.emit(self.module))
        self.duplicate_file_action = self._menu_action(file_menu, "Duplicate Script…", lambda: self.duplicate_requested.emit(self.module))
        file_menu.addSeparator()
        self.remove_action = self._menu_action(file_menu, "Remove Script…", lambda: self.remove_requested.emit(self.module))

        self.editor_edit_menu = QMenu("Edit", self)
        edit_menu = self.editor_edit_menu
        self.undo_action = self._menu_action(edit_menu, "Undo", self.editor.undo)
        self.redo_action = self._menu_action(edit_menu, "Redo", self.editor.redo)
        edit_menu.addSeparator()
        self.cut_action = self._menu_action(edit_menu, "Cut", self.editor.cut)
        self.copy_action = self._menu_action(edit_menu, "Copy", self.editor.copy)
        self.paste_action = self._menu_action(edit_menu, "Paste", self.editor.paste_safely)
        self.delete_action = self._menu_action(edit_menu, "Delete", self.editor.delete_selection_or_character)
        edit_menu.addSeparator()
        self.comment_action = self._menu_action(edit_menu, "Toggle Comment", self.editor.toggle_comment)
        self.duplicate_line_action = self._menu_action(edit_menu, "Duplicate Line or Selection", self.editor.duplicate_current_line_or_selection)
        self.select_all_action = self._menu_action(edit_menu, "Select All", self.editor.select_all_text)
        edit_menu.addSeparator()
        self.find_next_action = self._menu_action(edit_menu, "Find Next", self.find_next, shortcut="F3")
        self.find_previous_action = self._menu_action(edit_menu, "Find Previous", self.find_previous, shortcut="Shift+F3")
        self.clear_search_action = self._menu_action(edit_menu, "Clear Search", self.clear_search, shortcut="Esc")
        self.replace_action = self._menu_action(edit_menu, "Replace", self.replace_current)
        self.replace_all_action = self._menu_action(edit_menu, "Replace All", self.replace_all)
        self.goto_action = self._menu_action(edit_menu, "Go to Line…", self.show_go_to_line)

        self.editor_view_menu = QMenu("View", self)
        view_menu = self.editor_view_menu
        self.view_only_action = self._menu_action(view_menu, "View Only", self.toggle_view_only, checkable=True)
        view_menu.addSeparator()
        self.word_wrap_action = self._menu_action(view_menu, "Word Wrap", self.toggle_word_wrap, checkable=True)
        self.line_numbers_action = self._menu_action(view_menu, "Line Numbers", self.toggle_line_numbers, checkable=True)
        self.font_action = self._menu_action(view_menu, "Display Font…", self.choose_display_font)

        self.editor_run_menu = QMenu("Run", self)
        run_menu = self.editor_run_menu
        self.launch_action = self._menu_action(run_menu, "Run Script", lambda: self.launch_requested.emit(self.module))
        self.terminal_action = self._menu_action(run_menu, "Run in Terminal", lambda: self.terminal_requested.emit(self.module))
        self.admin_terminal_action = self._menu_action(run_menu, "Run as Administrator in Terminal", lambda: self.admin_terminal_requested.emit(self.module))
        self.arguments_action = self._menu_action(run_menu, "Run with Arguments…", lambda: self.run_with_arguments_requested.emit(self.module))
        run_menu.addSeparator()
        self.syntax_action = self._menu_action(run_menu, "Syntax / Lint Check", lambda: self.syntax_lint_requested.emit(self.module))
        self.interpreter_action = self._menu_action(run_menu, "Select Interpreter…", lambda: self.interpreter_requested.emit(self.module))
        self.working_directory_action = self._menu_action(run_menu, "Working Directory…", lambda: self.working_directory_requested.emit(self.module))
        self.environment_action = self._menu_action(run_menu, "Environment Profiles…", lambda: self.environment_profiles_requested.emit(self.module))
        run_menu.addSeparator()
        self.stop_action = self._menu_action(run_menu, "Stop", lambda: self.stop_requested.emit(self.module))
        self.force_stop_action = self._menu_action(run_menu, "Force Stop", lambda: self.force_stop_requested.emit(self.module))
        run_menu.addSeparator()
        self.executable_action = self._menu_action(
            run_menu,
            "Make Executable",
            lambda: self.executable_toggle_requested.emit(self.module),
        )

    def _connect_signals(self) -> None:
        self.editor.document().modificationChanged.connect(self._on_modification_changed)
        self.editor.document().undoAvailable.connect(self._emit_undo_redo_state)
        self.editor.document().redoAvailable.connect(self._emit_undo_redo_state)
        self.editor.paste_rejected.connect(self.status_message)
        self.editor.go_to_line_requested.connect(self.show_go_to_line)
        self.editor.view_only_edit_attempt.connect(self.show_view_only_edit_prompt)
        self.editor.overwrite_mode_changed.connect(self._update_operation_mode)
        self.editor.files_dropped.connect(
            lambda paths: self.external_files_dropped.emit(paths, self.module.path.parent)
        )
        self.editor.cursorPositionChanged.connect(self._update_cursor_position)
        self.repository.module_changed.connect(self._on_repository_module_changed)
        self.repository.module_path_changed.connect(self._on_module_path_changed)

        self.launch_button.clicked.connect(
            lambda: self.launch_requested.emit(self.module)
        )
        self.terminal_button.clicked.connect(
            lambda: self.terminal_requested.emit(self.module)
        )
        self.admin_button.clicked.connect(
            lambda: self.admin_terminal_requested.emit(self.module)
        )
        self.stop_button.clicked.connect(
            lambda: self.stop_requested.emit(self.module)
        )
        self.force_stop_button.clicked.connect(
            lambda: self.force_stop_requested.emit(self.module)
        )
        self.executable_button.clicked.connect(
            lambda: self.executable_toggle_requested.emit(self.module)
        )
        self.cancel_changes_button.clicked.connect(self.confirm_reload)
        self.save_changes_button.clicked.connect(self.save_to_disk)

        self.find_input.returnPressed.connect(self.find_next)
        self.find_input.textChanged.connect(lambda _text: self._refresh_search_highlights())
        self.case_sensitive.toggled.connect(lambda _checked: self._refresh_search_highlights())

    def _emit_undo_redo_state(self, *_args) -> None:
        document = self.editor.document()
        undo_available = document.isUndoAvailable() and not self.view_only
        redo_available = document.isRedoAvailable() and not self.view_only
        self.undo_action.setEnabled(undo_available)
        self.redo_action.setEnabled(redo_available)
        self.undo_redo_changed.emit(undo_available, redo_available)

    def apply_preferences(self) -> None:
        self.word_wrap_action.setChecked(bool(self.config.get("editor_word_wrap", False)))
        self.line_numbers_action.setChecked(bool(self.config.get("editor_line_numbers", True)))
        self.editor.set_word_wrap_enabled(self.word_wrap_action.isChecked())
        self.editor.set_line_numbers_visible(self.line_numbers_action.isChecked())
        self.editor.set_tab_width_spaces(
            self.config.get_int("editor_tab_width_spaces", 4, minimum=1, maximum=16)
        )
        fixed = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        family = str(self.config.get("editor_font_family", "") or "").strip() or fixed.family()
        size = self.config.get_int("editor_font_size", 10, minimum=6, maximum=72)
        weight = self.config.get_int("editor_font_weight", 400, minimum=100, maximum=900)
        font = QFont(family, size)
        try:
            font.setWeight(QFont.Weight(weight))
        except (TypeError, ValueError):
            font.setWeight(QFont.Weight.Normal)
        font.setItalic(bool(self.config.get("editor_font_italic", False)))
        self.editor.set_editor_font(font)
        self.editor_status.setVisible(bool(self.config.get("show_status_bar", True)))

    def toggle_word_wrap(self, checked: bool) -> None:
        self.config.set("editor_word_wrap", bool(checked), save=True)
        self.preferences_changed.emit()

    def toggle_line_numbers(self, checked: bool) -> None:
        self.config.set("editor_line_numbers", bool(checked), save=True)
        self.preferences_changed.emit()

    def choose_display_font(self) -> None:
        selected, accepted = QFontDialog.getFont(self.editor.font(), self, "Display Font")
        if not accepted:
            return
        self.config.update({
            "editor_font_family": selected.family(),
            "editor_font_size": selected.pointSize(),
            "editor_font_weight": int(selected.weight()),
            "editor_font_italic": selected.italic(),
        }, save=True)
        self.preferences_changed.emit()

    def toggle_view_only(self, checked: bool) -> None:
        requested = bool(checked)
        if self.view_only and not requested:
            response = QMessageBox.question(
                self, "Disable View Only?",
                "View Only protects this script from accidental changes. Disable it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if response != QMessageBox.StandardButton.Yes:
                self.view_only_action.blockSignals(True)
                self.view_only_action.setChecked(True)
                self.view_only_action.blockSignals(False)
                return
        self.view_only = requested
        if requested:
            self._view_only_notice_shown = False
        self.editor.set_view_only(requested)
        self.replace_input.setReadOnly(requested)
        for action in (self.undo_action, self.redo_action, self.cut_action, self.paste_action, self.delete_action, self.comment_action, self.duplicate_line_action, self.replace_action, self.replace_all_action):
            action.setEnabled(not requested)
        self.status_message.emit("View Only mode enabled." if requested else "View Only mode disabled.")
        self.preferences_changed.emit()

    def show_view_only_edit_prompt(self) -> None:
        self.status_message.emit("Editing is disabled while View Only mode is enabled.")
        if self._view_only_notice_shown:
            return
        self._view_only_notice_shown = True
        QMessageBox.information(
            self, "View Only Mode",
            "Editing is disabled because View Only mode is enabled. Use View → View Only in the embedded editor menu to enable editing.",
        )

    def _update_operation_mode(self, overwrite: bool) -> None:
        self.operation_mode_label.setText("Overwrite" if overwrite else "Insert")

    def _update_cursor_position(self) -> None:
        cursor = self.editor.textCursor()
        self.position_label.setText(
            f"Ln {cursor.blockNumber() + 1}/{self.editor.blockCount()}, "
            f"Col {cursor.positionInBlock() + 1}, Char {cursor.position()}"
        )

    def _refresh_search_highlights(self) -> None:
        query = self.find_input.text()[: self.MAX_SEARCH_QUERY_CHARACTERS]
        self._search_matches = []
        self._current_search_index = -1
        self._search_results_truncated = False
        if not query:
            self.editor.clear_search_selections()
            self._update_search_counter()
            return

        flags = QTextDocument.FindFlag(0)
        if self.case_sensitive.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively

        selections: list[QTextEdit.ExtraSelection] = []
        cursor = QTextCursor(self.editor.document())
        for _ in range(self.MAX_SEARCH_MATCHES):
            found = self.editor.document().find(query, cursor, flags)
            if found.isNull():
                break
            match_start = found.selectionStart()
            match_end = found.selectionEnd()
            self._search_matches.append((match_start, match_end))
            selection = QTextEdit.ExtraSelection()
            selection.cursor = found
            selection.format.setBackground(self.palette().alternateBase())
            selections.append(selection)
            cursor = QTextCursor(found)
            cursor.setPosition(match_end)
        else:
            probe = self.editor.document().find(query, cursor, flags)
            self._search_results_truncated = not probe.isNull()

        self.editor.set_search_selections(selections)
        self._update_search_counter_from_cursor()

    def _update_search_counter(self) -> None:
        total = len(self._search_matches)
        current = (
            self._current_search_index + 1
            if self._current_search_index >= 0
            else 0
        )
        suffix = "+" if self._search_results_truncated else ""
        self.search_counter.setText(f"{current}/{total}{suffix}")

    def _update_search_counter_from_cursor(self) -> None:
        cursor = self.editor.textCursor()
        pair = (cursor.selectionStart(), cursor.selectionEnd())
        try:
            self._current_search_index = self._search_matches.index(pair)
        except ValueError:
            self._current_search_index = -1
        self._update_search_counter()

    def clear_search(self) -> None:
        self.find_input.clear()
        self._search_matches = []
        self._current_search_index = -1
        self._search_results_truncated = False
        self.editor.clear_search_selections()
        self._update_search_counter()
        self.editor.setFocus()

    def find_previous(self) -> bool:
        text = self.find_input.text()
        if not text:
            return False
        flags = QTextDocument.FindFlag.FindBackward
        if self.case_sensitive.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        found = self.editor.find(text, flags)
        if not found:
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.editor.setTextCursor(cursor)
            found = self.editor.find(text, flags)
            if found:
                self.status_message.emit(f"Wrapped to bottom: found '{text}'")
        if not found:
            self.status_message.emit(f"Text not found: '{text}'")
        self._update_search_counter_from_cursor()
        return found

    def show_properties_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Properties")
        dialog.setMinimumWidth(520)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        try:
            stat_result = self.module.path.stat()
            permissions = oct(stat_result.st_mode & 0o777)
            modified = str(self.module.modified)
            size = f"{stat_result.st_size:,} bytes"
        except OSError:
            permissions = modified = size = "Unavailable"
        rows = (
            ("Name:", self.module.filename),
            ("Location:", str(self.module.path.parent)),
            ("Full path:", str(self.module.path)),
            ("Size:", size),
            ("Modified:", modified),
            ("Permissions:", permissions),
            ("Executable:", "Yes" if self.module.executable else "No"),
            ("Lines:", f"{self.editor.blockCount():,}"),
            ("Characters:", f"{max(0, self.editor.document().characterCount() - 1):,}"),
            ("Encoding:", self.file_encoding),
            ("Newline:", {"\n": "LF", "\r\n": "CRLF", "\r": "CR"}.get(self.file_newline, "LF")),
            ("View Only:", "On" if self.view_only else "Off"),
            ("Edit mode:", "Overwrite" if self.editor.overwriteMode() else "Insert"),
        )
        for label, value in rows:
            field = QLabel(value)
            field.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            field.setWordWrap(True)
            form.addRow(label, field)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, dialog)
        buttons.rejected.connect(dialog.reject)
        buttons.clicked.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def _decode_source(self, data: bytes) -> tuple[str, str, bytes]:
        """Decode a Python source file while honoring BOM/PEP 263 declarations."""
        bom_map = (
            (codecs.BOM_UTF32_LE, "utf-32-le"),
            (codecs.BOM_UTF32_BE, "utf-32-be"),
            (codecs.BOM_UTF8, "utf-8"),
            (codecs.BOM_UTF16_LE, "utf-16-le"),
            (codecs.BOM_UTF16_BE, "utf-16-be"),
        )
        for bom, encoding in bom_map:
            if data.startswith(bom):
                return data[len(bom):].decode(encoding, errors="strict"), encoding, bom

        try:
            detected, _lines = tokenize.detect_encoding(io.BytesIO(data).readline)
            return data.decode(detected, errors="strict"), detected, b""
        except (LookupError, SyntaxError, UnicodeDecodeError):
            system_encoding = locale.getpreferredencoding(False) or "utf-8"
            choices = [
                "Windows-1252",
                "ISO-8859-1",
                "UTF-16 LE",
                "UTF-16 BE",
                f"System encoding ({system_encoding})",
            ]
            selected, accepted = QInputDialog.getItem(
                self,
                "Choose Source Encoding",
                f"{self.module.filename} is not valid UTF-8 or a recognised Python source encoding.\n\nOpen using:",
                choices,
                0,
                False,
            )
            if not accepted:
                raise UnicodeDecodeError("utf-8", data, 0, min(1, len(data)), "opening cancelled")
            encoding = {
                "Windows-1252": "cp1252",
                "ISO-8859-1": "iso-8859-1",
                "UTF-16 LE": "utf-16-le",
                "UTF-16 BE": "utf-16-be",
                f"System encoding ({system_encoding})": system_encoding,
            }[selected]
            return data.decode(encoding, errors="strict"), encoding, b""

    @staticmethod
    def _looks_binary_text(text: str) -> bool:
        if "\x00" in text:
            return True
        if not text:
            return False
        controls = sum(
            1 for char in text
            if ord(char) < 32 and char not in "\t\n\r\f\b"
        )
        return controls / len(text) > 0.02

    @staticmethod
    def _detect_newline_style(content: str) -> str:
        crlf = content.count("\r\n")
        lf = content.count("\n") - crlf
        cr = content.count("\r") - crlf
        count, newline = max(((crlf, "\r\n"), (lf, "\n"), (cr, "\r")))
        return newline if count else "\n"

    def load_from_disk(self, *, show_errors: bool = True) -> bool:
        """Load one stable regular Python file with bounded decoding."""
        try:
            data, snapshot = read_regular_file(self.module.path, self.MAX_FILE_BYTES)
            text, encoding, bom = self._decode_source(data)
            if self._looks_binary_text(text):
                raise UnsupportedFileError("The file appears to contain binary control data.")
            if len(text) > self.editor.MAX_DOCUMENT_CHARACTERS:
                raise FileTooLargeError(
                    "The decoded document exceeds Python Lair's editor safety limit."
                )
        except FileTooLargeError as error:
            if show_errors:
                QMessageBox.warning(self, "File Too Large", str(error))
            self.status_message.emit(f"Could not load {self.module.filename}: {error}")
            return False
        except UnsupportedFileError as error:
            if show_errors:
                QMessageBox.warning(self, "Unsupported File", str(error))
            self.status_message.emit(f"Could not load {self.module.filename}: {error}")
            return False
        except FileStateChangedError as error:
            if show_errors:
                QMessageBox.warning(self, "File Changed", str(error))
            self.status_message.emit(f"Could not load {self.module.filename}: {error}")
            return False
        except UnicodeDecodeError as error:
            if show_errors:
                QMessageBox.warning(self, "Encoding Error", str(error))
            self.status_message.emit(f"Could not load {self.module.filename}: {error}")
            return False
        except (OSError, MemoryError) as error:
            if show_errors:
                QMessageBox.critical(
                    self,
                    "Could Not Open File",
                    f"Could not read {self.module.filename}:\n\n{error}",
                )
            self.status_message.emit(f"Could not load {self.module.filename}: {error}")
            return False

        newline = self._detect_newline_style(text)
        normalised = text.replace("\r\n", "\n").replace("\r", "\n")
        self._ignore_document_signal = True
        try:
            self.editor.load_text(normalised)
            self.editor.document().clearUndoRedoStacks()
            self.editor.mark_clean()
        finally:
            self._ignore_document_signal = False

        self.file_encoding = encoding
        self.file_bom = bom
        self.file_newline = newline
        self.file_disk_snapshot = snapshot
        self._loaded_mtime_ns = snapshot.state.mtime_ns
        self._external_change_pending = False
        self.external_banner.hide()
        self.module.loaded = True
        self.module.modified = snapshot.state.mtime_ns / 1_000_000_000
        self.module.size = snapshot.state.size
        self.module.executable = bool(snapshot.state.target_mode & 0o111)
        self.repository.set_dirty(self.module.path, False)
        self._refresh_header()
        self._update_cursor_position()
        self._refresh_search_highlights()
        self.encoding_status_label.setText(self.file_encoding.upper())
        self.status_message.emit(f"Loaded {self.module.filename}")
        return True

    def save_to_disk(self) -> bool:
        """Safely save while preserving encoding, newline style and file mode."""
        expected = self.file_disk_snapshot
        if self._external_change_pending and self.editor.is_modified:
            try:
                _disk_data, current = read_regular_file(
                    self.module.path, self.MAX_FILE_BYTES
                )
            except FileNotFoundError:
                current = None
            except OSError as error:
                QMessageBox.warning(
                    self,
                    "File Check Failed",
                    f"Python Lair could not verify the file before saving:\n\n{error}",
                )
                return False

            if current != expected:
                response = QMessageBox.question(
                    self,
                    "File Changed Externally",
                    "The file changed on disk. Saving now will replace that external "
                    "version with the text currently in this editor. Continue?",
                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
                if response != QMessageBox.StandardButton.Save:
                    return False
                expected = current

        content = self.editor.toPlainText()
        if self.file_newline != "\n":
            content = content.replace("\n", self.file_newline)
        try:
            payload = self.file_bom + content.encode(self.file_encoding, errors="strict")
        except UnicodeEncodeError as error:
            QMessageBox.critical(
                self,
                "Encoding Error",
                f"The edited text cannot be represented as {self.file_encoding}:\n\n{error}",
            )
            return False
        if len(payload) > self.MAX_FILE_BYTES:
            message = (
                f"The file exceeds Python Lair's "
                f"{self.MAX_FILE_BYTES // (1024 * 1024)} MiB editor safety limit."
            )
            QMessageBox.warning(self, "Save Cancelled", message)
            self.status_message.emit(message)
            return False

        temporary: Path | None = None
        descriptor: int | None = None
        try:
            if expected is None:
                if self.module.path.exists() or self.module.path.is_symlink():
                    raise FileStateChangedError(
                        "A file appeared at the save location. Saving was cancelled."
                    )
                write_path = self.module.path
                existing_mode = 0o666
            else:
                if current_file_state(self.module.path) != expected.state:
                    raise FileStateChangedError(
                        "The file changed again before Python Lair could save it."
                    )
                write_path = (
                    validated_symlink_target(self.module.path, expected.state)
                    if expected.state.is_symlink
                    else self.module.path
                )
                existing_mode = expected.state.target_mode & 0o7777

            parent = write_path.parent
            descriptor, raw_path = tempfile.mkstemp(
                prefix=f".{write_path.name}.python-lair-",
                suffix=".tmp",
                dir=parent,
            )
            temporary = Path(raw_path)
            if hasattr(os, "fchmod"):
                os.fchmod(descriptor, existing_mode)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = None
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())

            if expected is None:
                install_new_file_from_temp(temporary, write_path)
                temporary = None
            else:
                if current_file_state(self.module.path) != expected.state:
                    raise FileStateChangedError(
                        "The file changed again before Python Lair could replace it."
                    )
                if expected.state.is_symlink and validated_symlink_target(
                    self.module.path, expected.state
                ) != write_path:
                    raise FileStateChangedError(
                        "The symbolic-link target changed before replacement."
                    )
                os.replace(temporary, write_path)
                temporary = None
            fsync_directory(parent)
        except FileStateChangedError as error:
            QMessageBox.warning(self, "Save Cancelled", str(error))
            return False
        except OSError as error:
            QMessageBox.critical(self, "Save Failed", str(error))
            self.status_message.emit(f"Could not save {self.module.filename}: {error}")
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

        try:
            snapshot = snapshot_from_payload(self.module.path, payload)
            stat_result = self.module.path.stat()
            self.file_disk_snapshot = snapshot
            self._loaded_mtime_ns = snapshot.state.mtime_ns
            self.module.modified = stat_result.st_mtime
            self.module.size = stat_result.st_size
            self.module.executable = bool(stat_result.st_mode & 0o111)
        except OSError:
            self.file_disk_snapshot = None
            self._loaded_mtime_ns = None

        self._ignore_document_signal = True
        try:
            self.editor.mark_clean()
        finally:
            self._ignore_document_signal = False

        self._external_change_pending = False
        self.external_banner.hide()
        self.repository.set_dirty(self.module.path, False)
        self.repository.module_changed.emit(self.module)
        self._refresh_header()
        self.saved.emit(self.module)
        self.status_message.emit(f"Saved {self.module.filename}")
        return True

    def confirm_reload(self) -> None:
        if self.editor.is_modified:
            response = QMessageBox.question(
                self,
                "Discard Changes",
                "Discard all unsaved changes and reload this file from disk?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if response != QMessageBox.StandardButton.Yes:
                return
        self.load_from_disk()

    def find_next(self) -> bool:
        text = self.find_input.text()
        if not text:
            return False

        flags = QTextDocument.FindFlag(0)
        if self.case_sensitive.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively

        found = self.editor.find(text, flags)
        if not found:
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)
            found = self.editor.find(text, flags)
            if found:
                self.status_message.emit(f"Wrapped to top: found '{text}'")

        if not found:
            self.status_message.emit(f"Text not found: '{text}'")
        else:
            self._last_find_text = text
        return found

    def replace_current(self) -> bool:
        if self.view_only:
            self.show_view_only_edit_prompt()
            return False
        cursor = self.editor.textCursor()
        wanted = self.find_input.text()
        selected = cursor.selectedText()
        matches = selected == wanted
        if not self.case_sensitive.isChecked():
            matches = selected.casefold() == wanted.casefold()

        if wanted and matches:
            replacement = self.replace_input.text()
            document_length = max(0, self.editor.document().characterCount() - 1)
            selected_length = abs(cursor.selectionEnd() - cursor.selectionStart())
            if (
                document_length - selected_length + len(replacement)
                > self.editor.MAX_DOCUMENT_CHARACTERS
            ):
                self.status_message.emit(
                    "The replacement would exceed Python Lair's document safety limit."
                )
                return False
            cursor.insertText(replacement)
            self.editor.setTextCursor(cursor)
            self._refresh_search_highlights()
            self.find_next()
            return True
        return self.find_next()

    def replace_all(self) -> int:
        if self.view_only:
            self.show_view_only_edit_prompt()
            return 0
        wanted = self.find_input.text()
        if not wanted:
            return 0

        replacement = self.replace_input.text()
        source = self.editor.toPlainText()
        if self.case_sensitive.isChecked():
            count = source.count(wanted)
            result = source.replace(wanted, replacement)
        else:
            import re
            pattern = re.compile(re.escape(wanted), re.IGNORECASE)
            result, count = pattern.subn(lambda _match: replacement, source)

        if count:
            # Use the same hardened full-document path as large Paste. This
            # avoids bypassing the bracket/highlighter safeguards.
            if not self.editor.replace_document_text(result):
                return 0
            self._refresh_search_highlights()
            self.status_message.emit(f"Replaced {count} occurrence(s)")
        else:
            self.status_message.emit(f"Text not found: '{wanted}'")
        return count

    def show_go_to_line(self) -> None:
        line, accepted = QInputDialog.getInt(
            self,
            "Go to Line",
            f"Line number (1–{self.editor.blockCount()}):",
            self.editor.textCursor().blockNumber() + 1,
            1,
            max(1, self.editor.blockCount()),
        )
        if accepted:
            self.editor.go_to_line(line)

    def can_close(self) -> bool:
        """Ask whether an unsaved page may be closed."""
        if not self.editor.is_modified:
            return True

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Unsaved Changes")
        box.setText(f"Save changes to {self.module.filename}?")
        save = box.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
        cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()

        clicked = box.clickedButton()
        if clicked is save:
            return self.save_to_disk()
        if clicked is discard:
            return True
        # Cancel, closing the dialog via its title-bar button, or any unknown
        # result must preserve the unsaved editor.
        return False

    def _on_modification_changed(self, modified: bool) -> None:
        if self._ignore_document_signal:
            return
        self.repository.set_dirty(self.module.path, modified)
        self._refresh_header()

    def _on_module_path_changed(self, changed: Module, _old_path: Path) -> None:
        if changed is not self.module:
            return
        self._refresh_header()
        try:
            self._loaded_mtime_ns = self.module.path.stat().st_mtime_ns
        except OSError:
            self._loaded_mtime_ns = None

    def _on_repository_module_changed(self, changed: Module) -> None:
        if changed is not self.module and changed.path != self.module.path:
            return

        self._refresh_header()
        try:
            disk_mtime_ns = self.module.path.stat().st_mtime_ns
        except OSError:
            return

        if self._loaded_mtime_ns is None:
            self._loaded_mtime_ns = disk_mtime_ns
            return

        if disk_mtime_ns != self._loaded_mtime_ns:
            self._external_change_pending = True
            self.external_banner.show()

    def _reload_external_change(self) -> None:
        if self.editor.is_modified:
            response = QMessageBox.question(
                self,
                "Discard Editor Changes",
                "Reloading will discard your unsaved editor changes. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if response != QMessageBox.StandardButton.Yes:
                return
        self.load_from_disk()

    def _keep_editor_version(self) -> None:
        try:
            _payload, snapshot = read_regular_file(
                self.module.path, self.MAX_FILE_BYTES
            )
            self.file_disk_snapshot = snapshot
            self._loaded_mtime_ns = snapshot.state.mtime_ns
        except OSError:
            self.file_disk_snapshot = None
            self._loaded_mtime_ns = None
        self._external_change_pending = False
        self.external_banner.hide()
        self.status_message.emit("Keeping the editor version; save to overwrite disk")

    def _refresh_header(self) -> None:
        dirty = " [Unsaved]" if self.module.dirty else ""
        running = " [Running]" if self.module.running else ""
        display_name = escape(self.module.display_name)
        path_text = escape(str(self.module.path))
        self.title_label.setText(
            f"<h2>{display_name}{dirty}{running}</h2>"
            f"{path_text}"
        )
        self.executable_action.setText(
            "Remove Executable Permission" if self.module.executable else "Make Executable"
        )
        self.executable_button.setText(
            "Remove Exec" if self.module.executable else "Make Exec"
        )
        self.executable_status_label.setText(
            "Exec: Yes" if self.module.executable else "Exec: No"
        )
        running = bool(self.module.running)
        self.launch_action.setEnabled(not running)
        self.terminal_action.setEnabled(not running)
        self.admin_terminal_action.setEnabled(not running)

        # Compact run-state swap:
        # idle => start controls; running => stop controls.
        for button in (
            self.launch_button,
            self.terminal_button,
            self.admin_button,
        ):
            button.setVisible(not running)
            button.setEnabled(not running)

        for button in (
            self.stop_button,
            self.force_stop_button,
        ):
            button.setVisible(running)
            button.setEnabled(running)

        self.arguments_action.setEnabled(not running)
        self.stop_action.setEnabled(running)
        self.force_stop_action.setEnabled(running)
