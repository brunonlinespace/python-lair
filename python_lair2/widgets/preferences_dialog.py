# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""User preferences for Python Lair 2."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from python_lair2.services.config_service import ConfigService
from python_lair2.widgets.ui_styles import style_button, style_line_edit


class PreferencesDialog(QDialog):
    """Preferences that affect the local user's application environment."""

    def __init__(
        self,
        config: ConfigService,
        current_workspace: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(620)

        root = QVBoxLayout(self)
        root.setSpacing(12)

        description = QLabel(
            "Choose the workspace Python Lair 2 should open on its next start."
        )
        description.setWordWrap(True)
        root.addWidget(description)

        form = QFormLayout()
        workspace_row = QHBoxLayout()
        self.workspace_input = QLineEdit(
            str(config.get("workspace_path") or current_workspace)
        )
        style_line_edit(self.workspace_input)
        browse = style_button(QPushButton("Browse…"))
        browse.clicked.connect(self._browse_workspace)
        workspace_row.addWidget(self.workspace_input, 1)
        workspace_row.addWidget(browse)
        form.addRow("Workspace folder:", workspace_row)
        root.addLayout(form)

        note = QLabel(
            "This will inform the location of your active workspace."
        )
        note.setWordWrap(True)
        root.addWidget(note)

        setup_row = QHBoxLayout()
        setup_note = QLabel(
            "Need to choose or create a workspace again?"
        )
        setup_button = style_button(
            QPushButton("Show Setup Assistant on Next Start"),
            size="compact",
            minimum_width=220,
        )
        setup_button.clicked.connect(self._schedule_setup_assistant)
        setup_row.addWidget(setup_note)
        setup_row.addStretch(1)
        setup_row.addWidget(setup_button)
        root.addLayout(setup_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _browse_workspace(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Select Python Lair 2 Workspace",
            self.workspace_input.text(),
        )
        if selected:
            self.workspace_input.setText(selected)

    def _save(self) -> None:
        workspace = self.workspace_input.text().strip()
        self.config.update(
            {"workspace_path": workspace or None},
            save=True,
        )
        self.accept()


    def _schedule_setup_assistant(self) -> None:
        self.config.update(
            {
                "setup_completed": False,
                "show_setup_assistant": True,
            },
            save=True,
        )
        QMessageBox.information(
            self,
            "Setup Assistant Scheduled",
            "The workspace setup assistant will appear the next time "
            "Python Lair 2 starts.",
        )
