# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Keyboard shortcuts reference dialog."""

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget


class ShortcutsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumWidth(520)
        root = QVBoxLayout(self)
        label = QLabel(
            "<h2>Keyboard Shortcuts</h2>"
            "<table cellspacing='8'>"
            "<tr><td><b>Ctrl+N</b></td><td>New script</td></tr>"
            "<tr><td><b>Ctrl+Shift+N</b></td><td>New folder</td></tr>"
            "<tr><td><b>Ctrl+O</b></td><td>Import scripts</td></tr>"
            "<tr><td><b>Ctrl+S</b></td><td>Save current script</td></tr>"
            "<tr><td><b>Ctrl+X / Ctrl+C / Ctrl+V</b></td><td>Cut / Copy / Paste</td></tr>"
            "<tr><td><b>Ctrl+F</b></td><td>Find text</td></tr>"
            "<tr><td><b>F3 / Shift+F3</b></td><td>Find next / previous</td></tr>"
            "<tr><td><b>Esc</b></td><td>Clear embedded-editor search</td></tr>"
            "<tr><td><b>Ctrl+H</b></td><td>Find and replace</td></tr>"
            "<tr><td><b>Ctrl+G</b></td><td>Go to line</td></tr>"
            "<tr><td><b>Ctrl+/</b></td><td>Toggle comment</td></tr>"
            "<tr><td><b>Ctrl+D</b></td><td>Duplicate line or selection</td></tr>"
            "<tr><td><b>Ctrl+Shift+D</b></td><td>Duplicate current script</td></tr>"
            "<tr><td><b>Ctrl+Alt+D</b></td><td>Show Dashboard</td></tr>"
            "<tr><td><b>F5</b></td><td>Run current script</td></tr>"
            "<tr><td><b>Shift+F5</b></td><td>Stop current script</td></tr>"
            "<tr><td><b>Ctrl+Shift+F5</b></td><td>Force stop current script</td></tr>"
            "<tr><td><b>Ctrl+Shift+T</b></td><td>Run in terminal</td></tr>"
            "<tr><td><b>Ctrl+Alt+Shift+T</b></td><td>Run as administrator in terminal</td></tr>"
            "<tr><td><b>Ctrl+Shift+R</b></td><td>Run with arguments</td></tr>"
            "<tr><td><b>Ctrl+Shift+L</b></td><td>Syntax / lint check</td></tr>"
            "<tr><td><b>Ctrl+Alt+X</b></td><td>Make / remove executable permission</td></tr>"
            "<tr><td><b>F11</b></td><td>Toggle full screen</td></tr>"
            "<tr><td><b>F1</b></td><td>Documentation</td></tr>"
            "</table>"
        )
        label.setWordWrap(True)
        root.addWidget(label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)
