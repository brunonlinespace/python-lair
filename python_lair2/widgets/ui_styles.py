# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native-PyQt control helpers for the pure-style experiment."""

from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QLineEdit, QPushButton


def style_button(
    button: QPushButton,
    *,
    role: str = "neutral",
    size: str = "large",
    minimum_width: int | None = None,
) -> QPushButton:
    """Return a native QPushButton without application QSS."""
    del role, size
    if minimum_width is not None:
        button.setMinimumWidth(minimum_width)
    return button


def style_line_edit(field: QLineEdit) -> QLineEdit:
    """Return a native QLineEdit without application QSS."""
    return field


def style_combo_box(combo: QComboBox, *, minimum_width: int = 150) -> QComboBox:
    """Return a native QComboBox while retaining the layout minimum width."""
    combo.setMinimumWidth(minimum_width)
    return combo
