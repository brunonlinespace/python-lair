# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Small visible shutdown-progress dialog."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QWidget

from python_lair2.widgets.loading_indicator import LoadingIndicator


class ClosingDialog(QDialog):
    """Display responsive feedback while clean shutdown completes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Closing Python Lair 2")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.indicator = LoadingIndicator(self, compact=True)
        layout.addWidget(self.indicator)

    def start(self) -> None:
        self.indicator.start(
            "Closing Python Lair…",
            "Preparing a clean shutdown.",
        )
        self.show()
        self.raise_()
        self.activateWindow()

    def set_stage(self, detail: str) -> None:
        self.indicator.set_detail(detail)
