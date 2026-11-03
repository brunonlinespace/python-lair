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
widgets/dashboard.py

Persistent dashboard with fast list/grid switching.
Cards are reused during filtering, sorting, and view changes.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from python_lair2.models.module import Module
from python_lair2.models.module_repository import ModuleRepository
from python_lair2.models.module_state_store import ModuleStateStore
from python_lair2.services.resources import icon_path
from python_lair2.widgets.dashboard_card import DashboardCard
from python_lair2.widgets.loading_indicator import LoadingIndicator
from python_lair2.widgets.ui_styles import style_button, style_combo_box, style_line_edit


class FlowLayout(QLayout):
    """Lightweight wrapping layout used by the grid dashboard."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        margin: int = 0,
        spacing: int = 12,
    ) -> None:
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self._items = []

    def addItem(self, item) -> None:
        self._items.append(item)
        self.invalidate()

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            self.invalidate()
            return item
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())

        margins = self.contentsMargins()
        size += QSize(
            margins.left() + margins.right(),
            margins.top() + margins.bottom(),
        )
        return size

    def clear(self) -> None:
        """Remove layout items without deleting their widgets."""
        while self.count():
            self.takeAt(0)

    def _do_layout(self, rect: QRect, *, test_only: bool) -> int:
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        # Cache each sizeHint once per layout pass.
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + spacing

            if next_x - spacing > rect.right() and x > rect.x():
                x = rect.x()
                y += line_height + spacing
                next_x = x + hint.width() + spacing
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))

            x = next_x
            line_height = max(line_height, hint.height())

        return y + line_height - rect.y()


class CurrentPageStack(QStackedWidget):
    """A stack whose scrollable size follows only the visible page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.currentChanged.connect(self._current_page_changed)

    def hasHeightForWidth(self) -> bool:
        widget = self.currentWidget()
        layout = widget.layout() if widget is not None else None
        return bool(layout is not None and layout.hasHeightForWidth())

    def heightForWidth(self, width: int) -> int:
        widget = self.currentWidget()
        if widget is None:
            return super().heightForWidth(width)

        layout = widget.layout()
        if layout is not None and layout.hasHeightForWidth():
            margins = self.contentsMargins()
            available = max(0, width - margins.left() - margins.right())
            return (
                layout.heightForWidth(available)
                + margins.top()
                + margins.bottom()
            )
        return widget.sizeHint().height()

    def sizeHint(self) -> QSize:
        widget = self.currentWidget()
        if widget is None:
            return super().sizeHint()

        hint = widget.sizeHint()
        width = max(1, self.viewport_width_hint())
        if self.hasHeightForWidth():
            hint.setHeight(self.heightForWidth(width))
        return hint

    def minimumSizeHint(self) -> QSize:
        widget = self.currentWidget()
        if widget is None:
            return super().minimumSizeHint()

        hint = widget.minimumSizeHint()
        width = max(1, self.viewport_width_hint())
        if self.hasHeightForWidth():
            hint.setHeight(self.heightForWidth(width))
        return hint

    def viewport_width_hint(self) -> int:
        """Return an existing geometry width without querying sizeHint()."""
        ancestor = self.parentWidget()
        while ancestor is not None:
            if isinstance(ancestor, QScrollArea):
                viewport_width = ancestor.viewport().width()
                if viewport_width > 0:
                    return viewport_width
                break
            ancestor = ancestor.parentWidget()

        for candidate in (
            self.width(),
            self.currentWidget().width() if self.currentWidget() else 0,
            self.parentWidget().width() if self.parentWidget() else 0,
        ):
            if candidate > 0:
                return candidate

        # Construction-time fallback only. Never call sizeHint() here because
        # this method is itself used by sizeHint().
        return 800

    def _current_page_changed(self, _index: int) -> None:
        self.updateGeometry()
        widget = self.currentWidget()
        if widget is not None:
            widget.updateGeometry()


class DashboardWidget(QWidget):
    """Dashboard that creates one persistent card per repository module."""

    module_open_requested = pyqtSignal(object)
    module_launch_requested = pyqtSignal(object)
    module_terminal_requested = pyqtSignal(object)
    module_stop_requested = pyqtSignal(object)
    module_force_stop_requested = pyqtSignal(object)
    module_remove_requested = pyqtSignal(object)
    refresh_requested = pyqtSignal()
    create_script_requested = pyqtSignal()
    create_folder_requested = pyqtSignal()
    sort_mode_changed = pyqtSignal(str)
    view_mode_changed = pyqtSignal(str)

    SORT_LABELS = {
        "Title (A-Z)": "title_az",
        "Title (Z-A)": "title_za",
        "Last Created": "created",
        "Last Modified": "modified",
    }
    VALID_VIEW_MODES = {"list", "grid"}

    def __init__(
        self,
        repository: ModuleRepository,
        states: ModuleStateStore,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.repository = repository
        self.states = states
        self._list_cards: dict[Path, DashboardCard] = {}
        self._grid_cards: dict[Path, DashboardCard] = {}
        self._layout_signatures: dict[Path, tuple[object, ...]] = {}
        self._sort_mode = "modified"
        self._view_mode = "list"
        self._query = ""
        self._loading = False

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)
        self._search_timer.timeout.connect(self._apply_filter_and_sort)

        self._build_ui()
        self._connect_repository()

        for module in repository:
            self._add_module(module)
        self._apply_filter_and_sort()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 26, 30, 26)
        root.setSpacing(12)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading_row = QHBoxLayout()
        heading_row.setSpacing(10)
        logo_label = QLabel()
        logo = QPixmap(str(icon_path("python-lair-2-64.png")))
        if not logo.isNull():
            logo_label.setPixmap(
                logo.scaled(
                    42,
                    42,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        logo_label.setFixedSize(46, 46)
        heading_row.addWidget(logo_label)
        heading = QLabel("<h1>Python Lair 2</h1>")
        heading_row.addWidget(heading)
        heading_row.addStretch(1)
        root.addLayout(heading_row)

        tip = QLabel(
            "Tip: Drag and drop Python (.py) scripts anywhere onto the "
            "Dashboard to add them to your workspace."
        )
        tip.setWordWrap(True)
        root.addWidget(tip)

        self.summary_label = QLabel()
        root.addWidget(self.summary_label)

        # Search occupies its own full-width row.
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search scripts by title or filename…")
        self.search_input.setClearButtonEnabled(True)
        style_line_edit(self.search_input)
        self.search_input.textChanged.connect(self._schedule_search)
        root.addWidget(self.search_input)

        # All dashboard actions sit on one consistent row below search.
        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.new_script_button = style_button(
            QPushButton("New Script"), role="primary"
        )
        self.new_folder_button = style_button(QPushButton("New Folder"))

        self.new_script_button.setToolTip(
            "Create a Python script in the workspace root"
        )
        self.new_folder_button.setToolTip(
            "Create a subfolder in the workspace root"
        )

        self.new_script_button.clicked.connect(self.create_script_requested)
        self.new_folder_button.clicked.connect(self.create_folder_requested)

        controls.addWidget(self.new_script_button)
        controls.addWidget(self.new_folder_button)
        controls.addStretch(1)

        # Older dashboard placement restored. These controls remain right
        # aligned and ordered: Refresh | Grid/List View | Sort.
        self.refresh_button = style_button(
            QPushButton("Refresh"),
            size="compact",
            minimum_width=88,
        )
        self.view_toggle_button = style_button(
            QPushButton("Grid View"),
            size="compact",
            minimum_width=88,
        )
        self.refresh_button.setToolTip("Refresh the workspace")
        self.view_toggle_button.setToolTip(
            "Switch between list and grid views"
        )
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.view_toggle_button.clicked.connect(self.toggle_view_mode)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(self.SORT_LABELS.keys())
        self.sort_combo.setCurrentText("Last Modified")
        style_combo_box(self.sort_combo, minimum_width=132)
        self.sort_combo.setMaximumWidth(150)
        self.sort_combo.currentTextChanged.connect(self._on_sort_changed)

        controls.addWidget(self.refresh_button)
        controls.addWidget(self.view_toggle_button)
        controls.addWidget(self.sort_combo)
        root.addLayout(controls)

        self.unsaved_banner = QLabel()
        self.unsaved_banner.setWordWrap(True)
        self.unsaved_banner.setFrameShape(QFrame.Shape.StyledPanel)
        self.unsaved_banner.hide()
        root.addWidget(self.unsaved_banner)

        self.loading_indicator = LoadingIndicator(self, compact=True)
        self.loading_indicator.start(
            "Preparing your workspace…",
            "Scanning folders and Python scripts. Large workspaces may take a moment.",
        )

        self.empty_label = QLabel()
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.empty_label.hide()
        root.addWidget(self.empty_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        self.view_stack = CurrentPageStack(self.scroll)

        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.view_stack.addWidget(self.list_host)

        self.grid_host = QWidget()
        self.grid_layout = FlowLayout(self.grid_host, margin=0, spacing=12)
        self.view_stack.addWidget(self.grid_host)

        self.scroll.setWidget(self.view_stack)

        # The content stack is always the expanding part of the Dashboard.
        # Keeping it visible during startup prevents the heading, tip, search,
        # and controls from spreading vertically across the window.
        self.content_stack = QStackedWidget(self)

        loading_page = QWidget(self.content_stack)
        loading_layout = QVBoxLayout(loading_page)
        loading_layout.setContentsMargins(0, 0, 0, 0)
        loading_layout.setSpacing(0)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        loading_layout.addWidget(
            self.loading_indicator,
            alignment=Qt.AlignmentFlag.AlignTop,
        )
        loading_layout.addStretch(1)

        self.content_stack.addWidget(loading_page)
        self.content_stack.addWidget(self.scroll)
        root.addWidget(self.content_stack, 1)

    def set_loading(self, loading: bool, message: str | None = None) -> None:
        """Show or hide the in-dashboard workspace preparation panel."""
        self._loading = loading
        for control in (
            self.search_input,
            self.new_script_button,
            self.new_folder_button,
            self.refresh_button,
            self.view_toggle_button,
            self.sort_combo,
        ):
            control.setEnabled(not loading)

        if loading:
            self.loading_indicator.start(
                message or "Preparing your workspace…",
                "Scanning folders and Python scripts. Large workspaces may take a moment.",
            )
            self.empty_label.hide()
            self.summary_label.hide()
            self.content_stack.setCurrentIndex(0)
        else:
            self.loading_indicator.stop()
            self.summary_label.show()
            self.content_stack.setCurrentWidget(self.scroll)
            self._apply_filter_and_sort()

    def set_loading_detail(self, detail: str) -> None:
        if self._loading:
            self.loading_indicator.set_detail(detail)

    def _connect_repository(self) -> None:
        self.repository.module_added.connect(self._add_module)
        self.repository.module_removed.connect(self._remove_module)
        self.repository.module_changed.connect(self._update_module)
        self.repository.module_path_changed.connect(self._on_module_path_changed)
        self.repository.repository_reset.connect(self._reset)
        self.repository.dirty_count_changed.connect(self._update_unsaved_banner)

    def _connect_card(self, card: DashboardCard) -> None:
        card.open_requested.connect(self.module_open_requested)
        card.launch_requested.connect(self.module_launch_requested)
        card.terminal_requested.connect(self.module_terminal_requested)
        card.stop_requested.connect(self.module_stop_requested)
        card.force_stop_requested.connect(self.module_force_stop_requested)
        card.remove_requested.connect(self.module_remove_requested)

    def _add_module(self, module: Module) -> None:
        if module.path in self._list_cards:
            return

        list_card = DashboardCard(
            module,
            self.list_host,
            view_mode="list",
        )
        grid_card = DashboardCard(
            module,
            self.grid_host,
            view_mode="grid",
        )
        self._connect_card(list_card)
        self._connect_card(grid_card)

        self._list_cards[module.path] = list_card
        self._grid_cards[module.path] = grid_card
        self._layout_signatures[module.path] = self._layout_signature(module)

        state = self.states.ensure(module.path)
        state.dashboard_card = list_card
        state.dashboard_grid_card = grid_card
        self._apply_filter_and_sort()

    def _remove_module(self, module: Module) -> None:
        list_card = self._list_cards.pop(module.path, None)
        grid_card = self._grid_cards.pop(module.path, None)
        self._layout_signatures.pop(module.path, None)

        if list_card is not None:
            self.list_layout.removeWidget(list_card)
            list_card.deleteLater()
        if grid_card is not None:
            self.grid_layout.removeWidget(grid_card)
            grid_card.deleteLater()

        self._apply_filter_and_sort()

    def _update_module(self, module: Module) -> None:
        """
        Refresh card content without disturbing layout for runtime-only changes.

        Running and dirty state changes are frequent and do not affect Title,
        Created, Modified, or search ordering. Rebuilding hundreds of cards for
        those changes caused the Grid view to jump vertically on Launch/Stop.
        """
        list_card = self._list_cards.get(module.path)
        grid_card = self._grid_cards.get(module.path)
        if list_card is None or grid_card is None:
            self._add_module(module)
            return

        old_signature = self._layout_signatures.get(module.path)
        new_signature = self._layout_signature(module)
        self._layout_signatures[module.path] = new_signature

        list_card.refresh()
        grid_card.refresh()

        if old_signature != new_signature:
            self._apply_filter_and_sort()
        else:
            total = len(self.repository)
            visible_count = len(self.repository.search(self._query))
            running = len(self.repository.running)
            self.summary_label.setText(
                f"Showing {visible_count} of {total} scripts · {running} running"
            )
            self._update_unsaved_banner(len(self.repository.dirty))

    def _on_module_path_changed(self, module: Module, old_path: Path) -> None:
        """Re-key both persistent presentations after rename or move."""
        old_key = self.repository.normalize_path(old_path)
        self._layout_signatures.pop(old_key, None)
        state = self.states.ensure(module.path)

        list_card = self._list_cards.pop(old_key, None)
        grid_card = self._grid_cards.pop(old_key, None)

        if list_card is None:
            list_card = state.dashboard_card
        if grid_card is None:
            grid_card = state.dashboard_grid_card

        if list_card is None or grid_card is None:
            if list_card is not None:
                list_card.deleteLater()
            if grid_card is not None:
                grid_card.deleteLater()
            self._add_module(module)
            return

        for card in (list_card, grid_card):
            card.module = module
            card.refresh()

        self._list_cards[module.path] = list_card
        self._grid_cards[module.path] = grid_card
        self._layout_signatures[module.path] = self._layout_signature(module)
        state.dashboard_card = list_card
        state.dashboard_grid_card = grid_card
        self._apply_filter_and_sort()

    def _reset(self) -> None:
        for card in (
            *self._list_cards.values(),
            *self._grid_cards.values(),
        ):
            card.deleteLater()
        self._list_cards.clear()
        self._grid_cards.clear()
        self._layout_signatures.clear()
        self.grid_layout.clear()
        self._apply_filter_and_sort()

    @staticmethod
    def _layout_signature(module: Module) -> tuple[object, ...]:
        """
        Return only fields capable of changing search or sort placement.

        Runtime fields such as running, dirty, and loaded deliberately do not
        participate.
        """
        return (
            module.search_title,
            module.search_filename,
            module.created,
            module.modified,
        )

    def _schedule_search(self, text: str) -> None:
        self._query = text.casefold().strip()
        self._search_timer.start()

    def _on_sort_changed(self, label: str) -> None:
        self._sort_mode = self.SORT_LABELS.get(label, "modified")
        self.sort_mode_changed.emit(self._sort_mode)
        self._apply_filter_and_sort()

    def toggle_view_mode(self) -> None:
        self.set_view_mode("grid" if self._view_mode == "list" else "list")

    def set_view_mode(self, mode: str) -> None:
        if mode not in self.VALID_VIEW_MODES:
            mode = "list"
        changed = mode != self._view_mode
        self._view_mode = mode
        self.view_toggle_button.setText(
            "List View" if mode == "grid" else "Grid View"
        )

        # Both card collections are already laid out. Switching is therefore
        # a constant-time stacked-page change with no card reparenting.
        self.view_stack.setCurrentWidget(
            self.grid_host if mode == "grid" else self.list_host
        )
        self.view_stack.updateGeometry()
        self.scroll.widget().updateGeometry()
        if changed:
            self.view_mode_changed.emit(mode)

    def view_mode(self) -> str:
        return self._view_mode


    def set_sort_mode(self, mode: str) -> None:
        if mode not in self.repository.VALID_SORT_MODES:
            mode = "modified"
        self._sort_mode = mode
        for label, value in self.SORT_LABELS.items():
            if value == mode:
                self.sort_combo.blockSignals(True)
                self.sort_combo.setCurrentText(label)
                self.sort_combo.blockSignals(False)
                break
        self._apply_filter_and_sort()

    def set_search_text(self, text: str) -> None:
        self.search_input.setText(text)

    def _detach_all_cards_from_layouts(self) -> None:
        """
        Remove every persistent card from both layouts without deleting it.

        Explicit removeWidget() calls are more reliable than deleting layout
        items when the same persistent widgets are repeatedly reordered.
        """
        for card in self._list_cards.values():
            self.list_layout.removeWidget(card)
            card.hide()

        for card in self._grid_cards.values():
            self.grid_layout.removeWidget(card)
            card.hide()

        self.list_layout.invalidate()
        self.grid_layout.invalidate()

    def _apply_filter_and_sort(self) -> None:
        if self._loading:
            return

        matched = self.repository.search(self._query)
        ordered_visible = self.repository.sorted(matched, self._sort_mode)

        # Reinsert only visible cards, in the exact sorted order.
        self._detach_all_cards_from_layouts()

        for module in ordered_visible:
            list_card = self._list_cards.get(module.path)
            grid_card = self._grid_cards.get(module.path)

            if list_card is not None:
                self.list_layout.addWidget(list_card)
                list_card.show()

            if grid_card is not None:
                self.grid_layout.addWidget(grid_card)
                grid_card.show()

        # Force Qt to recalculate layout order immediately.
        self.list_layout.invalidate()
        self.list_layout.activate()
        self.grid_layout.invalidate()
        self.grid_host.updateGeometry()
        self.grid_host.update()

        self.view_stack.setCurrentWidget(
            self.grid_host if self._view_mode == "grid" else self.list_host
        )
        self.view_stack.updateGeometry()

        total = len(self.repository)
        visible_count = len(ordered_visible)
        running = len(self.repository.running)
        self.summary_label.setText(
            f"Showing {visible_count} of {total} scripts · {running} running"
        )

        self.scroll.setVisible(True)
        self.empty_label.setVisible(not ordered_visible)
        if total == 0:
            self.empty_label.setText(
                "No Python scripts were found in the library."
            )
        elif not ordered_visible:
            self.empty_label.setText(
                "No scripts match the current search."
            )

        self._update_unsaved_banner(len(self.repository.dirty))

    def _update_unsaved_banner(self, count: int) -> None:
        self.unsaved_banner.setVisible(count > 0)
        if count:
            self.unsaved_banner.setText(
                f"You have unsaved changes in {count} "
                f"script{'s' if count != 1 else ''}."
            )
