# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
"""Lazy mini-dashboard for a workspace subfolder."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from python_lair2.models.module import Module
from python_lair2.models.module_repository import ModuleRepository
from python_lair2.models.workspace_folder import WorkspaceFolder
from python_lair2.widgets.dashboard_card import DashboardCard
from python_lair2.widgets.navigation import external_python_paths
from python_lair2.widgets.ui_styles import style_button, style_line_edit


class FolderDashboard(QWidget):
    """Shows scripts in one folder and exposes safe folder actions."""

    module_open_requested = pyqtSignal(object)
    module_launch_requested = pyqtSignal(object)
    module_terminal_requested = pyqtSignal(object)
    module_stop_requested = pyqtSignal(object)
    module_force_stop_requested = pyqtSignal(object)
    module_remove_requested = pyqtSignal(object)

    open_external_requested = pyqtSignal(object)
    terminal_folder_requested = pyqtSignal(object)
    rename_folder_requested = pyqtSignal(object)
    remove_folder_requested = pyqtSignal(object)
    create_script_requested = pyqtSignal(object)
    create_folder_requested = pyqtSignal(object)
    external_files_dropped = pyqtSignal(object, object)

    def __init__(
        self,
        folder: WorkspaceFolder,
        repository: ModuleRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.folder = folder
        self.repository = repository
        self._cards: dict[Path, DashboardCard] = {}
        self._include_subfolders = True
        self._query = ""
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)
        self._search_timer.timeout.connect(self.refresh_contents)

        self._build_ui()
        self._connect_repository()
        self.refresh_contents()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(12)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        self.title_label = QLabel()
        self.title_label.setWordWrap(False)
        self.title_label.setTextFormat(Qt.TextFormat.PlainText)
        title_row.addWidget(self.title_label)
        title_row.addStretch(1)
        root.addLayout(title_row)

        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        root.addWidget(self.path_label)

        # Match the editor page: prominent actions at the top.
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.new_script_button = style_button(
            QPushButton("New Script"), role="primary"
        )
        self.new_folder_button = style_button(QPushButton("New Subfolder"))
        self.open_button = style_button(QPushButton("Open Externally"))
        self.terminal_button = style_button(
            QPushButton("Open Terminal"), role="terminal"
        )
        self.rename_button = style_button(QPushButton("Rename Folder"))
        self.remove_button = style_button(
            QPushButton("Remove Folder"), role="danger"
        )
        for button in (
            self.new_script_button,
            self.new_folder_button,
            self.open_button,
            self.terminal_button,
            self.rename_button,
            self.remove_button,
        ):
            actions.addWidget(button)
        actions.addStretch(1)
        root.addLayout(actions)

        # Folder pages now have the same search affordance as the Dashboard.
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search scripts in this folder by title or filename…"
        )
        self.search_input.setClearButtonEnabled(True)
        style_line_edit(self.search_input)
        self.search_input.textChanged.connect(self._schedule_search)
        root.addWidget(self.search_input)

        options = QHBoxLayout()
        options.setSpacing(8)
        self.summary_label = QLabel()
        options.addWidget(self.summary_label)
        options.addStretch(1)
        self.include_subfolders = QCheckBox("Include scripts in nested folders")
        self.include_subfolders.setChecked(True)
        options.addWidget(self.include_subfolders)
        root.addLayout(options)

        tip = QLabel(
            "Tip: Drop external .py files anywhere on this page to import "
            "them directly into this folder. Internal script cards can still "
            "be dragged onto sidebar folders to move them."
        )
        tip.setWordWrap(True)
        root.addWidget(tip)

        self.empty_label = QLabel("No Python scripts were found in this folder.")
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.cards_host = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_host)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cards_layout.addWidget(self.empty_label)
        self.cards_layout.addStretch()
        self.scroll.setWidget(self.cards_host)
        root.addWidget(self.scroll, 1)

        self.new_script_button.clicked.connect(
            lambda: self.create_script_requested.emit(self.folder.path)
        )
        self.new_folder_button.clicked.connect(
            lambda: self.create_folder_requested.emit(self.folder.path)
        )
        self.open_button.clicked.connect(
            lambda: self.open_external_requested.emit(self.folder.path)
        )
        self.terminal_button.clicked.connect(
            lambda: self.terminal_folder_requested.emit(self.folder.path)
        )
        self.rename_button.clicked.connect(
            lambda: self.rename_folder_requested.emit(self.folder.path)
        )
        self.remove_button.clicked.connect(
            lambda: self.remove_folder_requested.emit(self.folder.path)
        )
        self.include_subfolders.toggled.connect(self._set_include_subfolders)
        self._refresh_header()

    def _connect_repository(self) -> None:
        self.repository.module_added.connect(self._on_repository_change)
        self.repository.module_removed.connect(self._on_repository_change)
        self.repository.module_changed.connect(self._on_repository_change)
        self.repository.module_path_changed.connect(self._on_module_path_changed)
        self.repository.repository_reset.connect(self.refresh_contents)

    def _set_include_subfolders(self, checked: bool) -> None:
        self._include_subfolders = checked
        self.refresh_contents()

    def _matches(self, module: Module) -> bool:
        if self._include_subfolders:
            try:
                module.path.relative_to(self.folder.path)
                return True
            except ValueError:
                return False
        return module.path.parent == self.folder.path

    def modules(self) -> list[Module]:
        selected = [
            module
            for module in self.repository
            if self._matches(module)
            and (
                not self._query
                or self._query in module.search_title
                or self._query in module.search_filename
            )
        ]
        return self.repository.sorted(selected, mode="title_az")

    def _schedule_search(self, text: str) -> None:
        self._query = text.casefold().strip()
        self._search_timer.start()

    def refresh_contents(self) -> None:
        modules = self.modules()
        wanted = {module.path for module in modules}

        for path in tuple(self._cards):
            if path not in wanted:
                card = self._cards.pop(path)
                self.cards_layout.removeWidget(card)
                card.deleteLater()

        for index, module in enumerate(modules):
            card = self._cards.get(module.path)
            if card is None:
                card = DashboardCard(
                    module,
                    self.cards_host,
                    view_mode="list",
                )
                card.open_requested.connect(self.module_open_requested)
                card.launch_requested.connect(self.module_launch_requested)
                card.terminal_requested.connect(self.module_terminal_requested)
                card.stop_requested.connect(self.module_stop_requested)
                card.force_stop_requested.connect(self.module_force_stop_requested)
                card.remove_requested.connect(self.module_remove_requested)
                self._cards[module.path] = card
            else:
                card.refresh()
            # Insert cards before the empty-state label and bottom stretch.
            self.cards_layout.insertWidget(index, card)

        matching_total = sum(1 for module in self.repository if self._matches(module))
        self.summary_label.setText(
            f"Showing {len(modules)} of {matching_total} "
            f"script{'s' if matching_total != 1 else ''}"
        )
        self.empty_label.setVisible(not modules)
        if matching_total == 0:
            self.empty_label.setText(
                "No Python scripts were found in this folder."
            )
        elif not modules:
            self.empty_label.setText(
                "No scripts match the current folder search."
            )
        # Keep the scroll area visible so it remains the expanding section
        # and the header/actions stay pinned to the top even when empty.
        self.scroll.setVisible(True)
        self._refresh_header()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if external_python_paths(event.mimeData()):
            self._set_drop_highlight(True)
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if external_python_paths(event.mimeData()):
            self._set_drop_highlight(True)
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._set_drop_highlight(False)
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = external_python_paths(event.mimeData())
        self._set_drop_highlight(False)
        if not paths:
            event.ignore()
            return

        QTimer.singleShot(
            0,
            lambda dropped=paths, destination=self.folder.path:
                self.external_files_dropped.emit(dropped, destination),
        )
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()

    def _set_drop_highlight(self, active: bool) -> None:
        # Native-style experiment: no application-defined drop highlight.
        del active

    def update_folder_path(self, new_path: Path) -> None:
        self.folder = WorkspaceFolder(new_path, self.folder.workspace_root)
        self._refresh_header()
        self.refresh_contents()

    def _refresh_header(self) -> None:
        self.title_label.setText(self.folder.name)
        self.path_label.setText(str(self.folder.relative_path))
        root = self.folder.is_workspace_root
        self.rename_button.setEnabled(not root)
        self.remove_button.setEnabled(not root)

    def _on_module_path_changed(self, module: Module, _old_path: Path) -> None:
        self.refresh_contents()

    def _on_repository_change(self, module: Module) -> None:
        # A move can affect both the old and new folder. Refreshing this one
        # lightweight page is safe and keeps cards accurate.
        self.refresh_contents()
