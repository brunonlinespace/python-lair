# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fixed list and grid dashboard-card presentations."""

from __future__ import annotations

from datetime import datetime
from html import escape

from PyQt6.QtCore import QMimeData, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QDrag, QMouseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from python_lair2.models.module import Module
from python_lair2.widgets.ui_styles import style_button


class DashboardCard(QFrame):
    """
    Persistent card bound to one Module.

    A card is created for one presentation mode and never changes its internal
    layout. The main Dashboard keeps separate list and grid card instances, so
    switching view mode only changes the visible stacked page.
    """

    open_requested = pyqtSignal(object)
    launch_requested = pyqtSignal(object)
    terminal_requested = pyqtSignal(object)
    stop_requested = pyqtSignal(object)
    force_stop_requested = pyqtSignal(object)
    remove_requested = pyqtSignal(object)

    VALID_MODES = {"list", "grid"}

    def __init__(
        self,
        module: Module,
        parent=None,
        *,
        view_mode: str = "list",
    ) -> None:
        super().__init__(parent)
        self.module = module
        self._view_mode = view_mode if view_mode in self.VALID_MODES else "list"
        self._drag_start = QPoint()
        self._drag_active = False

        self.setObjectName("dashboardCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Plain)

        self._build_labels()
        self._build_buttons()
        self._build_fixed_layout()
        self.refresh()

    def _build_labels(self) -> None:
        self.title_label = QLabel()
        self.title_label.setTextFormat(Qt.TextFormat.RichText)
        self.title_label.setWordWrap(True)

        self.status_label = QLabel()
        self.status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
        )

        self.metadata_label = QLabel()
        self.metadata_label.setWordWrap(True)

    def _build_buttons(self) -> None:
        grid = self._view_mode == "grid"

        self.launch_button = self._button(
            "▶" if grid else "Launch",
            role="primary",
            grid=grid,
        )
        self.terminal_button = self._button(
            ">_" if grid else "Terminal",
            role="terminal",
            grid=grid,
        )
        self.stop_button = self._button(
            "■" if grid else "Stop",
            role="warning",
            grid=grid,
        )
        self.force_stop_button = self._button(
            "✕" if grid else "Force Stop",
            role="danger",
            grid=grid,
        )
        self.edit_button = self._button(
            "✎" if grid else "Edit",
            role="neutral",
            grid=grid,
        )
        tooltips = {
            self.launch_button: "Launch script",
            self.terminal_button: "Open script in an external terminal",
            self.stop_button: "Stop the running script",
            self.force_stop_button: "Force-stop a hanging script",
            self.edit_button: "Open in the embedded editor",
        }
        for button, tooltip in tooltips.items():
            button.setToolTip(tooltip)

        self.launch_button.clicked.connect(
            lambda: self.launch_requested.emit(self.module)
        )
        self.terminal_button.clicked.connect(
            lambda: self.terminal_requested.emit(self.module)
        )
        self.stop_button.clicked.connect(
            lambda: self.stop_requested.emit(self.module)
        )
        self.force_stop_button.clicked.connect(
            lambda: self.force_stop_requested.emit(self.module)
        )
        self.edit_button.clicked.connect(
            lambda: self.open_requested.emit(self.module)
        )

    def _build_fixed_layout(self) -> None:
        if self._view_mode == "grid":
            self._build_grid_layout()
        else:
            self._build_list_layout()

    def _build_list_layout(self) -> None:
        self.setMinimumSize(0, 118)
        self.setMaximumWidth(16777215)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(self.title_label, 1)
        header.addWidget(self.status_label)
        outer.addLayout(header)
        outer.addWidget(self.metadata_label)

        actions = QHBoxLayout()
        actions.setSpacing(7)
        actions.addStretch(1)
        for button in (
            self.launch_button,
            self.terminal_button,
            self.stop_button,
            self.force_stop_button,
            self.edit_button,
        ):
            actions.addWidget(button)
        outer.addLayout(actions)

    def _build_grid_layout(self) -> None:
        self.setMinimumSize(300, 245)
        self.setMaximumWidth(360)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )

        outer = QGridLayout(self)
        outer.setContentsMargins(14, 12, 12, 12)
        outer.setHorizontalSpacing(12)
        outer.setVerticalSpacing(8)
        outer.setColumnStretch(0, 1)
        outer.setColumnStretch(1, 0)

        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(self.title_label, 1)
        header.addWidget(self.status_label)
        content.addLayout(header)
        content.addWidget(self.metadata_label)
        content.addStretch(1)

        actions = QVBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(6)
        actions.setAlignment(Qt.AlignmentFlag.AlignTop)
        for button in (
            self.launch_button,
            self.terminal_button,
            self.stop_button,
            self.force_stop_button,
            self.edit_button,
        ):
            actions.addWidget(button, alignment=Qt.AlignmentFlag.AlignRight)
        actions.addStretch(1)

        outer.addLayout(content, 0, 0)
        outer.addLayout(
            actions,
            0,
            1,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
        )

    @staticmethod
    def _button(
        text: str,
        *,
        role: str,
        grid: bool,
    ) -> QPushButton:
        button = style_button(
            QPushButton(text),
            role=role,
            size="compact",
            minimum_width=40 if grid else 80,
        )
        if grid:
            button.setFixedSize(40, 32)
        return button

    @staticmethod
    def format_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"

    def refresh(self) -> None:
        executable = " [Executable]" if self.module.executable else ""
        display_name = escape(self.module.display_name)
        self.title_label.setText(f"<b>{display_name}</b>{executable}")

        statuses: list[str] = []
        if self.module.dirty:
            statuses.append("● Unsaved")
        if self.module.running:
            statuses.append("● Running")
        self.status_label.setText("<br>".join(statuses))

        modified = datetime.fromtimestamp(self.module.modified).strftime(
            "%Y-%m-%d %H:%M"
        )
        folder = escape(self.module.folder or ".")
        filename = escape(self.module.filename)
        self.metadata_label.setText(
            f"{folder}/{filename}<br>"
            f"Modified: {modified} · Size: {self.format_size(self.module.size)}"
        )

        self.launch_button.setEnabled(not self.module.running)
        if self._view_mode == "grid":
            self.launch_button.setText("…" if self.module.running else "▶")
        else:
            self.launch_button.setText(
                "Running" if self.module.running else "Launch"
            )
        self.stop_button.setVisible(self.module.running)
        self.force_stop_button.setVisible(self.module.running)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_requested.emit(self.module)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._drag_active:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = QPoint()
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_active:
            event.accept()
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return super().mouseMoveEvent(event)
        if self._drag_start.isNull():
            return super().mouseMoveEvent(event)
        if (
            event.position().toPoint() - self._drag_start
        ).manhattanLength() < 10:
            return super().mouseMoveEvent(event)

        self._drag_active = True
        try:
            mime = QMimeData()
            mime.setData(
                "application/x-python-lair-module",
                str(self.module.path).encode("utf-8"),
            )
            drag = QDrag(self)
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)
        finally:
            self._drag_active = False
            self._drag_start = QPoint()
        event.accept()
