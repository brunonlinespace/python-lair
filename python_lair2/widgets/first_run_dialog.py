# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""First-run workspace setup assistant."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from python_lair2.services.runtime_paths import RuntimePaths
from python_lair2.widgets.ui_styles import style_button, style_line_edit


class FirstRunWizard(QWizard):
    """Small, one-time assistant for choosing a writable workspace."""

    def __init__(
        self,
        runtime_paths: RuntimePaths,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.runtime_paths = runtime_paths
        self._selected_workspace = runtime_paths.default_workspace

        self.setWindowTitle("Welcome to Python Lair 2")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(690, 450)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        self.setOption(QWizard.WizardOption.NoBackButtonOnLastPage, True)

        if runtime_paths.icon_path.exists():
            pixmap = QPixmap(str(runtime_paths.icon_path))
            if not pixmap.isNull():
                self.setPixmap(
                    QWizard.WizardPixmap.LogoPixmap,
                    pixmap.scaled(
                        72,
                        72,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    ),
                )

        self.addPage(self._welcome_page())
        self.addPage(self._workspace_page())
        self.addPage(self._finish_page())

        self.currentIdChanged.connect(self._update_finish_page)

    @property
    def selected_workspace(self) -> Path:
        """Workspace selected when the assistant is accepted."""
        return self._selected_workspace

    def _welcome_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Welcome to Python Lair 2")
        page.setSubTitle(
            "Organize, launch, and edit your Python script collection."
        )

        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        description = QLabel(
            "Python Lair keeps application files separate from your scripts. "
            "This assistant will choose the writable workspace that appears "
            "in the sidebar and Dashboard."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        runtime_note = QLabel(
            f"Current edition: <b>{self.runtime_paths.runtime_label}</b>"
        )
        runtime_note.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(runtime_note)

        if self.runtime_paths.running_as_appimage:
            appimage_note = QLabel(
                "The AppImage itself is read-only. Your scripts will remain "
                "in a normal writable folder outside the AppImage."
            )
            appimage_note.setWordWrap(True)
            layout.addWidget(appimage_note)

        layout.addStretch(1)
        return page

    def _workspace_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Choose your workspace")
        page.setSubTitle(
            "You can change this later from Edit → Preferences."
        )

        root = QVBoxLayout(page)
        root.setSpacing(12)

        self.default_radio = QRadioButton("Use the recommended workspace")
        self.default_radio.setChecked(True)
        root.addWidget(self.default_radio)

        default_path = QLabel(str(self.runtime_paths.default_workspace))
        default_path.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        root.addWidget(default_path)

        self.existing_radio = QRadioButton("Use an existing folder")
        root.addWidget(self.existing_radio)

        existing_row = QHBoxLayout()
        existing_row.setContentsMargins(24, 0, 0, 5)
        self.existing_input = QLineEdit()
        self.existing_input.setPlaceholderText("Select an existing workspace…")
        style_line_edit(self.existing_input)
        existing_browse = style_button(
            QPushButton("Browse…"),
            size="compact",
            minimum_width=90,
        )
        existing_browse.clicked.connect(self._browse_existing)
        existing_row.addWidget(self.existing_input, 1)
        existing_row.addWidget(existing_browse)
        root.addLayout(existing_row)

        self.new_radio = QRadioButton("Create a new workspace")
        root.addWidget(self.new_radio)

        new_row = QHBoxLayout()
        new_row.setContentsMargins(24, 0, 0, 0)
        self.new_input = QLineEdit()
        self.new_input.setText(str(self.runtime_paths.default_workspace))
        self.new_input.setPlaceholderText("Enter a new workspace path…")
        style_line_edit(self.new_input)
        new_browse = style_button(
            QPushButton("Choose location…"),
            size="compact",
            minimum_width=125,
        )
        new_browse.clicked.connect(self._browse_new_parent)
        new_row.addWidget(self.new_input, 1)
        new_row.addWidget(new_browse)
        root.addLayout(new_row)

        for field, radio in (
            (self.existing_input, self.existing_radio),
            (self.new_input, self.new_radio),
        ):
            field.textEdited.connect(lambda _text, target=radio: target.setChecked(True))

        root.addStretch(1)
        return page

    def _finish_page(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Ready to begin")
        page.setSubTitle("Python Lair will prepare and scan this workspace.")

        layout = QFormLayout(page)
        self.finish_path = QLabel()
        self.finish_path.setWordWrap(True)
        self.finish_path.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addRow("Workspace:", self.finish_path)

        note = QLabel(
            "The main window will open immediately and display an animated "
            "workspace preparation message while the folder tree is built."
        )
        note.setWordWrap(True)
        layout.addRow(note)
        return page

    def validateCurrentPage(self) -> bool:  # noqa: N802
        """Validate the workspace choice before advancing."""
        if self.currentId() != 1:
            return True

        candidate = self._candidate_workspace()
        if candidate is None:
            QMessageBox.warning(
                self,
                "Choose a Workspace",
                "Please choose or enter a valid workspace folder.",
            )
            return False

        if self.existing_radio.isChecked() and not candidate.is_dir():
            QMessageBox.warning(
                self,
                "Folder Not Found",
                "The selected existing workspace does not exist.",
            )
            return False

        self._selected_workspace = candidate
        return True

    def accept(self) -> None:
        candidate = self._candidate_workspace()
        if candidate is not None:
            self._selected_workspace = candidate
        super().accept()

    def _candidate_workspace(self) -> Path | None:
        if self.default_radio.isChecked():
            return self.runtime_paths.default_workspace.resolve(strict=False)

        raw = (
            self.existing_input.text()
            if self.existing_radio.isChecked()
            else self.new_input.text()
        ).strip()
        if not raw:
            return None
        return Path(raw).expanduser().resolve(strict=False)

    def _browse_existing(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Choose Existing Python Lair Workspace",
            str(Path.home()),
        )
        if selected:
            self.existing_input.setText(selected)
            self.existing_radio.setChecked(True)

    def _browse_new_parent(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Choose Where to Create the Workspace",
            str(Path.home()),
        )
        if selected:
            self.new_input.setText(
                str(Path(selected) / "Python Lair Workspace")
            )
            self.new_radio.setChecked(True)

    def _update_finish_page(self, page_id: int) -> None:
        if page_id == 2:
            candidate = self._candidate_workspace()
            self.finish_path.setText(
                str(candidate or self.runtime_paths.default_workspace)
            )
