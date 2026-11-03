# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reusable in-window busy indicator for workspace operations."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class LoadingIndicator(QFrame):
    """Small animated status panel that does not block the Qt event loop."""

    _FRAMES = ("◐", "◓", "◑", "◒")

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        compact: bool = False,
    ) -> None:
        super().__init__(parent)
        self._frame_index = 0
        self._compact = compact

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Plain)

        if compact:
            layout = QHBoxLayout(self)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(10)
            layout.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
            # Do not cap the height: translated or wrapped detail text must
            # remain fully visible on narrow windows.
            self.setMinimumHeight(72)
        else:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(28, 24, 28, 24)
            layout.setSpacing(8)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spinner_label = QLabel(self._FRAMES[0])
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_host = QWidget(self)
        text_layout = QVBoxLayout(text_host)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.detail_label = QLabel()
        self.detail_label.setWordWrap(True)

        text_layout.addWidget(self.message_label)
        text_layout.addWidget(self.detail_label)

        layout.addWidget(self.spinner_label)
        layout.addWidget(text_host, 1)

        self._timer = QTimer(self)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self._advance)
        self.hide()

    def start(self, message: str, detail: str = "") -> None:
        self.message_label.setText(message)
        self.detail_label.setText(detail)
        self.detail_label.setVisible(bool(detail))
        self._frame_index = 0
        self.spinner_label.setText(self._FRAMES[0])
        self.show()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def set_detail(self, detail: str) -> None:
        self.detail_label.setText(detail)
        self.detail_label.setVisible(bool(detail))

    def _advance(self) -> None:
        self._frame_index = (self._frame_index + 1) % len(self._FRAMES)
        self.spinner_label.setText(self._FRAMES[self._frame_index])
