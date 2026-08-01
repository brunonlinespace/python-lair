#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#==============================================================================
# Linux Python Launcher & Editor
# Copyright (C) 2026 AI Collaborator / brunonlinespace
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# linux-python-suite-modular.py
# Version: 55 (Safeguarded Drag & Drop Re-parenting Pointer Handling Fix)
#=============================================================================

import os
import sys
import json
import stat
import shutil
import subprocess
from datetime import datetime
from PyQt6.QtCore import Qt, QUrl, QRect, QSize, QPoint
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QAction, QKeyEvent, QPainter, QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QTreeWidget, QTreeWidgetItem, QMessageBox, QTextEdit, QPlainTextEdit, QScrollArea, QLayout, QInputDialog, QLineEdit, QComboBox, QSplitter
)

MODULES_DIR = "modules"
CONFIG_FILE = "suite_config.json"

class FlowLayout(QLayout):
    """A safe, robust custom layout that arranges widgets in a wrapping flow structure."""
    def __init__(self, parent=None, margin=0, spacing=15):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def doLayout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self.itemList:
            space_x = spacing
            space_y = spacing
            
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and x > rect.x():
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()


class AccessibleTreeWidget(QTreeWidget):
    """Custom QTreeWidget supporting keyboard navigation and script re-parenting via drag-and-drop."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)

    def keyPressEvent(self, event: QKeyEvent):
        super().keyPressEvent(event)
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Home, Qt.Key.Key_End):
            current_item = self.currentItem()
            if current_item:
                self.itemClicked.emit(current_item, 0)

    def dropEvent(self, event: QDropEvent):
        dragged_item = self.currentItem()
        script_path = None
        if dragged_item:
            try:
                script_path = dragged_item.data(0, Qt.ItemDataRole.UserRole)
            except RuntimeError:
                dragged_item = None

        target_item = self.itemAt(event.position().toPoint())
        
        super().dropEvent(event)
        
        if script_path and script_path != "dashboard":
            target_rel_dir = ""
            if target_item:
                try:
                    target_data = target_item.data(0, Qt.ItemDataRole.UserRole)
                    if target_data == "dashboard":
                        target_rel_dir = ""
                    elif target_data and os.path.isfile(target_data):
                        # Dropped onto another file -> target directory is that file's parent directory relative to modules
                        target_rel_dir = os.path.dirname(os.path.relpath(target_data, MODULES_DIR))
                    elif target_data and os.path.isdir(target_data):
                        target_rel_dir = os.path.relpath(target_data, MODULES_DIR)
                    else:
                        # Folder item or layout node without direct file path stored
                        path_parts = []
                        curr = target_item
                        while curr and curr != self.topLevelItem(0) and curr.parent() is not None:
                            text = curr.text(0).replace("📁 ", "").replace("📦 ", "")
                            path_parts.insert(0, text)
                            curr = curr.parent()
                        target_rel_dir = os.path.join(*path_parts) if path_parts else ""
                except RuntimeError:
                    target_rel_dir = ""

            if target_rel_dir == "." or not target_rel_dir:
                target_rel_dir = ""

            filename = os.path.basename(script_path)
            new_dest_dir = os.path.join(MODULES_DIR, target_rel_dir) if target_rel_dir else MODULES_DIR
            os.makedirs(new_dest_dir, exist_ok=True)
            new_path = os.path.join(new_dest_dir, filename)

            if script_path != new_path:
                try:
                    shutil.move(script_path, new_path)
                    window = self.window()
                    if hasattr(window, "refresh_modules_from_disk"):
                        window.refresh_modules_from_disk()
                        window.jump_to_module_page(new_path)
                        window.update_status_label(f"Moved {filename} to folder '{target_rel_dir or 'Root'}'")
                except Exception as e:
                    QMessageBox.critical(self, "Move Error", f"Could not move script file: {e}")
                    window = self.window()
                    if hasattr(window, "refresh_modules_from_disk"):
                        window.refresh_modules_from_disk()


class LineNumberArea(QWidget):
    """Widget responsible for painting line numbers beside the CodeEditor."""
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    """Custom QPlainTextEdit featuring an integrated line-number margin gutter."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def line_number_area_width(self):
        digits = 1
        max_blocks = max(1, self.blockCount())
        while max_blocks >= 10:
            max_blocks //= 10
            digits += 1
        space = 15 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#2a2d2e")
            selection.format.setBackground(line_color)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#1e1e1e"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#858585"))
                painter.setFont(self.font())
                painter.drawText(0, top, self.line_number_area.width() - 8, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            if block.isValid():
                bottom = top + int(self.blockBoundingRect(block).height())
            else:
                bottom = top
            block_number += 1

class LinuxPythonLauncherEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Linux Python Launcher & Editor")
        self.resize(1350, 850)

        self.setAcceptDrops(True)

        self.dashboard_mode = self.load_dashboard_state()
        self.search_filter_text = ""
        self.sort_criterion = "modified"

        self.editors = {}
        self.original_contents = {}
        self.title_labels = {}
        self.chmod_buttons = {}
        self.current_script_path = "dashboard"
        self.is_navigating = False

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.processes = {}
        self.modules = self.discover_modules()

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #333338; width: 3px; }")
        self.main_layout.addWidget(self.splitter)

        self.setup_sidebar()
        self.setup_content_area()

    def load_dashboard_state(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("dashboard_mode", "list")
        except Exception:
            pass
        return "list"

    def save_dashboard_state(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump({"dashboard_mode": self.dashboard_mode}, f)
        except Exception as e:
            print(f"Error saving config: {e}")

    def discover_modules(self):
        modules_list = []
        if not os.path.exists(MODULES_DIR):
            os.makedirs(MODULES_DIR)
            
        for root, dirs, files in os.walk(MODULES_DIR):
            for filename in sorted(files):
                if filename.endswith(".py") and filename != "__init__.py":
                    script_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(script_path, MODULES_DIR)
                    display_name = filename[:-3].replace("-", " ").replace("_", " ").title()
                    
                    try:
                        stat_info = os.stat(script_path)
                        created_time = stat_info.st_ctime
                        modified_time = stat_info.st_mtime
                        file_size = stat_info.st_size
                        is_exec = bool(stat_info.st_mode & stat.S_IXUSR)
                    except Exception:
                        created_time = 0
                        modified_time = 0
                        file_size = 0
                        is_exec = False

                    modules_list.append({
                        "name": display_name,
                        "filename": filename,
                        "path": script_path,
                        "rel_path": rel_path,
                        "folder": os.path.dirname(rel_path),
                        "created": created_time,
                        "modified": modified_time,
                        "size": file_size,
                        "executable": is_exec
                    })
        return modules_list

    def sort_modules(self, mods):
        if self.sort_criterion == "title_za":
            return sorted(mods, key=lambda x: x['name'].lower(), reverse=True)
        elif self.sort_criterion == "created":
            return sorted(mods, key=lambda x: x['created'], reverse=True)
        elif self.sort_criterion == "modified":
            return sorted(mods, key=lambda x: x['modified'], reverse=True)
        else:
            return sorted(mods, key=lambda x: x['name'].lower())

    def setup_sidebar(self):
        sidebar = QFrame()
        sidebar.setMinimumWidth(200)
        sidebar.setStyleSheet("background-color: #252526; color: #ffffff;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)

        title_lbl = QLabel("<h3>🛠️ Workspace</h3>")
        sidebar_layout.addWidget(title_lbl)

        info_drop_lbl = QLabel("<font color='#9cdcfe'>💡 Tip: Drag scripts between folders or drop external .py files onto Dashboard!</font>")
        info_drop_lbl.setWordWrap(True)
        info_drop_lbl.setStyleSheet("font-size: 8.5pt; margin-bottom: 5px;")
        sidebar_layout.addWidget(info_drop_lbl)

        mode_btn_text = "🔲 Grid View" if self.dashboard_mode == "list" else "📋 List View"
        self.mode_toggle_btn = QPushButton(mode_btn_text)
        self.mode_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #333337; color: #ffffff; border: 1px solid #555;
                border-radius: 4px; padding: 6px; font-weight: bold; margin-bottom: 5px;
            }
            QPushButton:hover {
                background-color: #007acc; border-color: #007acc;
            }
        """)
        self.mode_toggle_btn.clicked.connect(self.toggle_dashboard_mode)
        sidebar_layout.addWidget(self.mode_toggle_btn)

        refresh_btn = QPushButton("🔄 Refresh Modules")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #333337; color: #dcdcdc; border: 1px solid #555; 
                border-radius: 4px; padding: 6px; font-weight: bold; margin-bottom: 10px;
            }
            QPushButton:hover {
                background-color: #3e3e42; border-color: #007acc;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_modules_from_disk)
        sidebar_layout.addWidget(refresh_btn)

        self.nav_tree = AccessibleTreeWidget()
        self.nav_tree.setHeaderHidden(True)
        self.nav_tree.setStyleSheet("""
            QTreeWidget { background-color: #252526; border: none; color: #dcdcdc; font-size: 11pt; }
            QTreeWidget::item { padding: 6px; border-radius: 4px; margin-bottom: 2px; }
            QTreeWidget::item:selected { background-color: #007acc; color: #ffffff; font-weight: bold; }
            QTreeWidget::item:hover:!selected { background-color: #3e3e42; }
        """)
        
        self.populate_nav_tree()
        self.nav_tree.itemClicked.connect(self.on_nav_item_clicked)
        self.nav_tree.currentItemChanged.connect(lambda current, previous: self.on_nav_item_clicked(current, 0) if current else None)
        sidebar_layout.addWidget(self.nav_tree, 1)

        self.status_lbl = QLabel()
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet("font-size: 9pt; margin-top: 5px;")
        self.update_status_label("Loaded successfully.")
        sidebar_layout.addWidget(self.status_lbl)

        self.splitter.addWidget(sidebar)

    def update_status_label(self, base_message="Ready."):
        unsaved_count = sum(1 for p in self.editors if self.has_unsaved_changes(p))
        if unsaved_count > 0:
            self.status_lbl.setText(f"Status: {base_message} <font color='#cca700'><b>(⚠️ {unsaved_count} unsaved)</b></font>")
        else:
            self.status_lbl.setText(f"Status: {base_message}")

    def refresh_modules_from_disk(self):
        old_count = len(self.modules)
        self.modules = self.discover_modules()
        self.populate_nav_tree()
        self.refresh_content_pages()
        
        self.jump_to_module_page(self.current_script_path)
        
        new_count = len(self.modules)
        diff = new_count - old_count
        
        if diff > 0:
            msg = f"Refreshed: Found {diff} new script(s)."
        elif diff < 0:
            msg = f"Refreshed: {abs(diff)} script(s) removed."
        else:
            msg = "Refreshed: Modules folder is up to date."
            
        self.update_status_label(msg)

    def populate_nav_tree(self):
        self.nav_tree.clear()
        
        dashboard_item = QTreeWidgetItem(self.nav_tree, ["🏠 Dashboard"])
        dashboard_item.setData(0, Qt.ItemDataRole.UserRole, "dashboard")
        self.nav_tree.addTopLevelItem(dashboard_item)
        
        sorted_mods = self.sort_modules(self.modules)
        folder_nodes = {}

        for mod in sorted_mods:
            folder_path = mod['folder']
            
            label_text = f"📦 {mod['name']}"
            if mod['path'] in self.editors and self.has_unsaved_changes(mod['path']):
                label_text += " ⚠️"

            if not folder_path or folder_path == ".":
                script_item = QTreeWidgetItem(self.nav_tree, [label_text])
                script_item.setData(0, Qt.ItemDataRole.UserRole, mod['path'])
            else:
                parent_widget = self.nav_tree
                parts = folder_path.split(os.sep)
                current_accumulated = ""
                for part in parts:
                    current_accumulated = os.path.join(current_accumulated, part) if current_accumulated else part
                    if current_accumulated not in folder_nodes:
                        folder_node = QTreeWidgetItem(parent_widget, [f"📁 {part}"])
                        folder_nodes[current_accumulated] = folder_node
                        parent_widget = folder_node
                    else:
                        parent_widget = folder_nodes[current_accumulated]

                script_item = QTreeWidgetItem(parent_widget, [label_text])
                script_item.setData(0, Qt.ItemDataRole.UserRole, mod['path'])
            
        self.nav_tree.expandAll()

    def update_nav_item_indicators(self):
        self.populate_nav_tree()
        self.jump_to_module_page(self.current_script_path)
                
        if self.current_script_path in self.title_labels:
            mod_info = next((m for m in self.modules if m['path'] == self.current_script_path), None)
            if mod_info:
                title_lbl = self.title_labels[self.current_script_path]
                if self.has_unsaved_changes(self.current_script_path):
                    title_lbl.setText(f"<h2>{mod_info['name']} <font color='#cca700' size='4'>[⚠️ Unsaved Modifications]</font></h2><font color='#858585'>{mod_info['path']}</font>")
                else:
                    title_lbl.setText(f"<h2>{mod_info['name']}</h2><font color='#858585'>{mod_info['path']}</font>")

        if self.current_script_path == "dashboard" and hasattr(self, 'dashboard_unsaved_banner'):
            unsaved_count = sum(1 for p in self.editors if self.has_unsaved_changes(p))
            if unsaved_count > 0:
                self.dashboard_unsaved_banner.setText(f"<b>⚠️ Warning: You have unsaved changes in {unsaved_count} script(s).</b> Switch to them from the sidebar to review or save.")
                self.dashboard_unsaved_banner.setVisible(True)
            else:
                self.dashboard_unsaved_banner.setVisible(False)

    def setup_content_area(self):
        self.stack = QStackedWidget()
        self.splitter.addWidget(self.stack)
        self.splitter.setSizes([260, 1090])

        self.refresh_content_pages()
        self.is_navigating = True
        
        root_item = self.nav_tree.topLevelItem(0)
        if root_item:
            self.nav_tree.setCurrentItem(root_item)
            
        self.is_navigating = False

    def toggle_dashboard_mode(self):
        if self.dashboard_mode == "list":
            self.dashboard_mode = "grid"
            self.mode_toggle_btn.setText("📋 List View")
        else:
            self.dashboard_mode = "list"
            self.mode_toggle_btn.setText("🔲 Grid View")
        
        self.save_dashboard_state()
        self.refresh_content_pages()
        self.jump_to_module_page(self.current_script_path)

    def format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def refresh_content_pages(self):
        self.editors.clear()
        self.original_contents.clear()
        self.title_labels.clear()
        self.chmod_buttons.clear()

        while self.stack.count() > 0:
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.deleteLater()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        dash_widget = QWidget()
        dash_layout = QVBoxLayout(dash_widget)
        dash_layout.setContentsMargins(30, 30, 30, 30)
        
        title_label = QLabel("<h1>Welcome to Linux Python Launcher & Editor</h1>")
        title_label.setWordWrap(True)
        dash_layout.addWidget(title_label)

        self.dashboard_unsaved_banner = QLabel()
        self.dashboard_unsaved_banner.setWordWrap(True)
        self.dashboard_unsaved_banner.setStyleSheet("""
            QLabel {
                background-color: #3b3012; border: 1px solid #cca700; color: #ffd700;
                padding: 10px; border-radius: 4px; font-size: 10pt; margin-top: 5px; margin-bottom: 5px;
            }
        """)
        unsaved_count_init = sum(1 for p in self.editors if self.has_unsaved_changes(p))
        if unsaved_count_init > 0:
            self.dashboard_unsaved_banner.setText(f"<b>⚠️ Warning: You have unsaved changes in {unsaved_count_init} script(s).</b> Switch to them from the sidebar to review or save.")
            self.dashboard_unsaved_banner.setVisible(True)
        else:
            self.dashboard_unsaved_banner.setVisible(False)
        dash_layout.addWidget(self.dashboard_unsaved_banner)

        desc_label = QLabel("<b>Drag and drop any Python (.py) script file directly onto this window</b> or edit files externally in the <b>modules/</b> folder, then click <b>Refresh Modules</b>.")
        desc_label.setWordWrap(True)
        dash_layout.addWidget(desc_label)
        
        dash_layout.addSpacing(10)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search scripts by title or filename...")
        self.search_input.setText(self.search_filter_text)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e; color: #dcdcdc; border: 1px solid #3f3f46;
                border-radius: 4px; padding: 8px; padding-right: 32px; font-size: 10pt;
            }
            QLineEdit:focus {
                border-color: #007acc;
            }
        """)
        self.search_input.returnPressed.connect(self.trigger_search)

        search_action = QAction("🔍", self.search_input)
        search_action.setToolTip("Click to search")
        search_action.triggered.connect(self.trigger_search)
        self.search_input.addAction(search_action, QLineEdit.ActionPosition.TrailingPosition)

        controls_layout.addWidget(self.search_input, 1)

        search_btn = QPushButton("Search")
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc; color: #ffffff; border: none;
                border-radius: 4px; padding: 8px 14px; font-weight: bold; font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #0098ff;
            }
        """)
        search_btn.clicked.connect(self.trigger_search)
        controls_layout.addWidget(search_btn)

        sort_label = QLabel("Sort by:")
        sort_label.setStyleSheet("color: #000000; font-weight: bold;")
        controls_layout.addWidget(sort_label)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Title (A-Z)", "Title (Z-A)", "Last Created", "Last Modified"])
        if self.sort_criterion == "title_za":
            self.sort_combo.setCurrentIndex(1)
        elif self.sort_criterion == "created":
            self.sort_combo.setCurrentIndex(2)
        elif self.sort_criterion == "modified":
            self.sort_combo.setCurrentIndex(3)
        else:
            self.sort_combo.setCurrentIndex(0)
            
        self.sort_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d30; color: #dcdcdc; border: 1px solid #3f3f46;
                border-radius: 4px; padding: 6px; font-size: 10pt;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #2d2d30; color: #dcdcdc; selection-background-color: #007acc; selection-color: #ffffff;
            }
        """)
        self.sort_combo.currentIndexChanged.connect(self.on_sort_changed)
        controls_layout.addWidget(self.sort_combo)

        dash_layout.addLayout(controls_layout)
        dash_layout.addSpacing(15)

        filtered_mods = [
            m for m in self.modules 
            if self.search_filter_text.lower() in m['name'].lower() or self.search_filter_text.lower() in m['filename'].lower()
        ]
        sorted_dashboard_mods = self.sort_modules(filtered_mods)

        if not self.modules:
            no_mod_lbl = QLabel("<i>No python scripts found. Add scripts to the modules folder or drop them here!</i>")
            no_mod_lbl.setWordWrap(True)
            no_mod_lbl.setStyleSheet("color: #d16969; margin-top: 15px;")
            dash_layout.addWidget(no_mod_lbl)
        elif not sorted_dashboard_mods:
            no_match_lbl = QLabel(f"<i>No scripts matched your search query '{self.search_filter_text}'.</i>")
            no_match_lbl.setWordWrap(True)
            no_match_lbl.setStyleSheet("color: #9cdcfe; margin-top: 15px;")
            dash_layout.addWidget(no_match_lbl)
        else:
            if self.dashboard_mode == "list":
                self.links_layout = QVBoxLayout()
                self.links_layout.setSpacing(12)

                for mod in sorted_dashboard_mods:
                    card_frame = QFrame()
                    card_frame.setStyleSheet("""
                        QFrame {
                            background-color: #1e1e1e;
                            border: 1px solid #333338;
                            border-radius: 6px;
                        }
                        QFrame:hover {
                            border: 1px solid #007acc;
                            background-color: #252526;
                        }
                    """)
                    card_layout = QHBoxLayout(card_frame)
                    card_layout.setContentsMargins(15, 12, 15, 12)
                    
                    exec_badge = " <font color='#4ec9b0' size='2'>[Executable]</font>" if mod['executable'] else ""
                    sub_folder_info = f" <font color='#858585' size='2'>({mod['rel_path']})</font>"
                    info_lbl = QLabel(f"<span style='color: #ffffff; font-size: 11pt;'><b>{mod['name']}</b></span>{exec_badge}{sub_folder_info}<br><span style='color: #858585; font-size: 9pt;'>{mod['path']}</span>")
                    info_lbl.setWordWrap(True)
                    info_lbl.setStyleSheet("border: none; background: transparent;")
                    
                    btn_layout = QHBoxLayout()
                    btn_layout.setSpacing(8)

                    launch_btn = QPushButton("▶ Launch")
                    launch_btn.setToolTip("Run script in standard background process")
                    launch_btn.setStyleSheet("background-color: #007acc; color: white; border: none; padding: 6px 10px; border-radius: 4px; font-weight: bold;")
                    launch_btn.clicked.connect(lambda checked, path=mod['path']: self.launch_external_persistent(path))

                    term_btn = QPushButton("Terminal")
                    term_btn.setToolTip("Launch TUI / script in an external interactive terminal emulator")
                    term_btn.setStyleSheet("background-color: #2d5a2d; color: #cfc; border: none; padding: 6px 10px; border-radius: 4px; font-weight: bold;")
                    term_btn.clicked.connect(lambda checked, path=mod['path']: self.launch_in_terminal(path))

                    edit_btn = QPushButton("Edit")
                    edit_btn.setStyleSheet("background-color: #333337; color: #dcdcdc; border: 1px solid #555; border-radius: 4px; padding: 6px 10px;")
                    edit_btn.clicked.connect(lambda checked, p=mod['path']: self.jump_to_module_page(p))

                    del_btn = QPushButton("Remove")
                    del_btn.setStyleSheet("background-color: #511; color: #f88; border: none; padding: 6px 10px; border-radius: 4px;")
                    del_btn.clicked.connect(lambda checked, path=mod['path']: self.remove_module(path))

                    btn_layout.addWidget(launch_btn)
                    btn_layout.addWidget(term_btn)
                    btn_layout.addWidget(edit_btn)
                    btn_layout.addWidget(del_btn)

                    card_layout.addWidget(info_lbl, 1)
                    card_layout.addLayout(btn_layout)

                    self.links_layout.addWidget(card_frame)

                dash_layout.addLayout(self.links_layout)

            else:
                self.flow_layout = FlowLayout(margin=0, spacing=12)

                for mod in sorted_dashboard_mods:
                    card_frame = QFrame()
                    card_frame.setFixedSize(270, 155)
                    card_frame.setStyleSheet("""
                        QFrame {
                            background-color: #1e1e1e;
                            border: 1px solid #333338;
                            border-radius: 6px;
                        }
                        QFrame:hover {
                            border: 1px solid #007acc;
                            background-color: #252526;
                        }
                    """)
                    grid_card_layout = QVBoxLayout(card_frame)
                    grid_card_layout.setContentsMargins(10, 10, 10, 10)
                    grid_card_layout.setSpacing(4)

                    exec_tag = " <font color='#4ec9b0'>[+x]</font>" if mod['executable'] else ""
                    title_lbl = QLabel(f"<b>📦 {mod['name']}</b>{exec_tag}")
                    title_lbl.setStyleSheet("color: #ffffff; font-size: 10pt; border: none; background: transparent;")
                    title_lbl.setWordWrap(True)
                    grid_card_layout.addWidget(title_lbl)

                    created_time_str = datetime.fromtimestamp(mod['created']).strftime('%Y-%m-%d %H:%M') if mod['created'] else "Unknown"
                    size_str = self.format_size(mod['size'])

                    meta_lbl = QLabel(f"<font color='#858585' size='2'>Path: {mod['rel_path']}<br>Created: {created_time_str}<br>Size: {size_str}</font>")
                    meta_lbl.setStyleSheet("border: none; background: transparent;")
                    meta_lbl.setWordWrap(True)
                    grid_card_layout.addWidget(meta_lbl)

                    grid_card_layout.addStretch()

                    grid_btn_layout = QHBoxLayout()
                    grid_btn_layout.setSpacing(4)

                    launch_btn = QPushButton("Launch")
                    launch_btn.setStyleSheet("background-color: #007acc; color: white; border: none; padding: 4px 6px; border-radius: 3px; font-weight: bold; font-size: 8pt;")
                    launch_btn.clicked.connect(lambda checked, path=mod['path']: self.launch_external_persistent(path))

                    term_btn = QPushButton("Terminal")
                    term_btn.setStyleSheet("background-color: #2d5a2d; color: #cfc; border: none; padding: 4px 6px; border-radius: 3px; font-weight: bold; font-size: 8pt;")
                    term_btn.clicked.connect(lambda checked, path=mod['path']: self.launch_in_terminal(path))

                    edit_btn = QPushButton("Edit")
                    edit_btn.setStyleSheet("background-color: #333337; color: #dcdcdc; border: 1px solid #555; border-radius: 3px; padding: 4px 6px; font-size: 8pt;")
                    edit_btn.clicked.connect(lambda checked, p=mod['path']: self.jump_to_module_page(p))

                    del_btn = QPushButton("Del")
                    del_btn.setStyleSheet("background-color: #511; color: #f88; border: none; padding: 4px 6px; border-radius: 3px; font-size: 8pt;")
                    del_btn.clicked.connect(lambda checked, path=mod['path']: self.remove_module(path))

                    grid_btn_layout.addWidget(launch_btn)
                    grid_btn_layout.addWidget(term_btn)
                    grid_btn_layout.addWidget(edit_btn)
                    grid_btn_layout.addWidget(del_btn)
                    grid_card_layout.addLayout(grid_btn_layout)

                    self.flow_layout.addWidget(card_frame)

                dash_layout.addLayout(self.flow_layout)

        dash_layout.addStretch()
        scroll_area.setWidget(dash_widget)
        self.stack.addWidget(scroll_area)

        sorted_mods_all = self.sort_modules(self.modules)
        for mod in sorted_mods_all:
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(20, 20, 20, 20)
            
            title_info = QLabel(f"<h2>{mod['name']}</h2><font color='#858585'>{mod['path']}</font>")
            title_info.setWordWrap(True)
            layout.addWidget(title_info)
            self.title_labels[mod['path']] = title_info

            btn_row = QHBoxLayout()
            btn_row.setSpacing(8)
            
            action_btn = QPushButton("▶ Launch")
            action_btn.setStyleSheet("padding: 8px 12px; font-weight: bold; background-color: #007acc; color: white; border: none; border-radius: 4px;")
            action_btn.clicked.connect(lambda checked, path=mod['path']: self.launch_external_persistent(path))

            term_action_btn = QPushButton("Terminal")
            term_action_btn.setStyleSheet("padding: 8px 12px; font-weight: bold; background-color: #2d5a2d; color: #cfc; border: none; border-radius: 4px;")
            term_action_btn.clicked.connect(lambda checked, path=mod['path']: self.launch_in_terminal(path))

            rename_btn = QPushButton("Rename")
            rename_btn.setStyleSheet("padding: 8px 12px; background-color: #333337; color: #dcdcdc; border: 1px solid #555; border-radius: 4px;")
            rename_btn.clicked.connect(lambda checked, path=mod['path']: self.rename_script_file(path))

            chmod_text = "Make Unexecutable" if mod['executable'] else "Make Executable"
            chmod_btn = QPushButton(chmod_text)
            chmod_btn.setStyleSheet("padding: 8px 12px; background-color: #333337; color: #dcdcdc; border: 1px solid #555; border-radius: 4px;")
            chmod_btn.clicked.connect(lambda checked, path=mod['path']: self.toggle_executable(path))
            self.chmod_buttons[mod['path']] = chmod_btn
            
            del_btn = QPushButton("Remove")
            del_btn.setStyleSheet("padding: 8px 12px; background-color: #511; color: #f88; border: none; border-radius: 4px;")
            del_btn.clicked.connect(lambda checked, path=mod['path']: self.remove_module(path))

            btn_row.addWidget(action_btn)
            btn_row.addWidget(term_action_btn)
            btn_row.addWidget(rename_btn)
            btn_row.addWidget(chmod_btn)
            btn_row.addWidget(del_btn)
            btn_row.addStretch()
            layout.addLayout(btn_row)

            editor_label = QLabel("<b>Embedded Script Editor:</b>")
            editor_label.setStyleSheet("margin-top: 10px;")
            layout.addWidget(editor_label)

            text_editor = CodeEditor()
            text_editor.setFont(QFont("Courier New", 10))
            text_editor.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; border: 1px solid #3f3f46; border-radius: 4px;")
            
            self.load_editor_content(mod['path'], text_editor)
            self.editors[mod['path']] = text_editor
            
            text_editor.textChanged.connect(lambda p=mod['path']: self.on_text_modified(p))

            layout.addWidget(text_editor)

            editor_btn_layout = QHBoxLayout()
            editor_btn_layout.addStretch()

            cancel_btn = QPushButton("↩ Cancel Changes")
            cancel_btn.setFixedWidth(150)
            cancel_btn.setStyleSheet("padding: 8px; background-color: #333337; color: #ccc; border: 1px solid #555; border-radius: 4px;")
            cancel_btn.clicked.connect(lambda checked, p=mod['path'], ed=text_editor: self.reload_module_code(p, ed))

            save_btn = QPushButton("💾 Save Changes")
            save_btn.setFixedWidth(160)
            save_btn.setStyleSheet("padding: 8px; background-color: #285228; color: #cfc; border: none; border-radius: 4px; font-weight: bold;")
            save_btn.clicked.connect(lambda checked, p=mod['path'], ed=text_editor: self.save_module_code(p, ed))
            
            editor_btn_layout.addWidget(cancel_btn)
            editor_btn_layout.addWidget(save_btn)
            layout.addLayout(editor_btn_layout)

            self.stack.addWidget(page)

    def trigger_search(self):
        if hasattr(self, 'search_input'):
            self.search_filter_text = self.search_input.text()
        current_cursor_pos = self.search_input.cursorPosition() if hasattr(self, 'search_input') else 0
        self.refresh_content_pages()
        if hasattr(self, 'search_input'):
            self.search_input.setFocus()
            self.search_input.setCursorPosition(min(current_cursor_pos, len(self.search_input.text())))

    def on_sort_changed(self, index):
        if index == 1:
            self.sort_criterion = "title_za"
        elif index == 2:
            self.sort_criterion = "created"
        elif index == 3:
            self.sort_criterion = "modified"
        else:
            self.sort_criterion = "title_az"
        
        self.populate_nav_tree()
        self.refresh_content_pages()
        self.jump_to_module_page(self.current_script_path)

    def jump_to_module_page(self, script_path):
        self.current_script_path = script_path
        if script_path == "dashboard":
            self.switch_view(0)
            self.is_navigating = True
            root_item = self.nav_tree.topLevelItem(0)
            if root_item:
                self.nav_tree.setCurrentItem(root_item)
            self.is_navigating = False
            return

        sorted_mods = self.sort_modules(self.modules)
        for idx, mod in enumerate(sorted_mods, start=1):
            if mod['path'] == script_path:
                self.switch_view(idx)
                break
        
        def find_and_select_item(parent_item):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                try:
                    if child.data(0, Qt.ItemDataRole.UserRole) == script_path:
                        self.is_navigating = True
                        self.nav_tree.setCurrentItem(child)
                        self.is_navigating = False
                        return True
                except RuntimeError:
                    continue
                if find_and_select_item(child):
                    return True
            return False

        for i in range(self.nav_tree.topLevelItemCount()):
            top_item = self.nav_tree.topLevelItem(i)
            try:
                if top_item.data(0, Qt.ItemDataRole.UserRole) == script_path:
                    self.is_navigating = True
                    self.nav_tree.setCurrentItem(top_item)
                    self.is_navigating = False
                    break
            except RuntimeError:
                continue
            if find_and_select_item(top_item):
                break

    def load_editor_content(self, script_path, editor):
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
                editor.setPlainText(content)
                self.original_contents[script_path] = content
        except Exception as e:
            err_msg = f"# Error loading file content: {e}"
            editor.setPlainText(err_msg)
            self.original_contents[script_path] = err_msg

    def reload_module_code(self, script_path, editor):
        confirm = QMessageBox.question(
            self, "Discard Changes", 
            "Are you sure you want to discard your unsaved changes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.load_editor_content(script_path, editor)
            self.update_nav_item_indicators()
            self.update_status_label(f"Discarded changes for {os.path.basename(script_path)}")

    def save_module_code(self, script_path, editor):
        try:
            content = editor.toPlainText()
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.original_contents[script_path] = content
            
            self.update_nav_item_indicators()
            self.update_status_label(f"Successfully saved changes to {os.path.basename(script_path)}")
            QMessageBox.information(self, "Success", f"Changes to {os.path.basename(script_path)} saved successfully!")
        except Exception as e:
            self.update_status_label(f"Error saving file ({e})")
            QMessageBox.critical(self, "Error", f"Could not save file: {e}")

    def has_unsaved_changes(self, script_path):
        if not script_path or script_path not in self.editors:
            return False
        editor = self.editors[script_path]
        current_text = editor.toPlainText()
        original_text = self.original_contents.get(script_path, "")
        return current_text != original_text

    def on_text_modified(self, script_path):
        self.update_nav_item_indicators()
        self.update_status_label(f"Modifying {os.path.basename(script_path)}")

    def on_nav_item_clicked(self, item, column):
        if self.is_navigating or not item:
            return

        try:
            target_path = item.data(0, Qt.ItemDataRole.UserRole)
        except RuntimeError:
            return

        if not target_path:
            return

        if target_path == self.current_script_path:
            return

        if self.current_script_path and self.current_script_path != "dashboard":
            if self.has_unsaved_changes(self.current_script_path):
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("Unsaved Modifications")
                msg_box.setText(f"You have unsaved changes in '{os.path.basename(self.current_script_path)}'.")
                msg_box.setInformativeText("Do you want to switch scripts without saving your modifications?")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg_box.setDefaultButton(QMessageBox.StandardButton.No)
                
                response = msg_box.exec()
                if response == QMessageBox.StandardButton.No:
                    self.jump_to_module_page(self.current_script_path)
                    return

        self.current_script_path = target_path
        if target_path == "dashboard":
            self.switch_view(0)
        else:
            sorted_mods = self.sort_modules(self.modules)
            for idx, mod in enumerate(sorted_mods, start=1):
                if mod['path'] == target_path:
                    self.switch_view(idx)
                    break
                    
        self.update_nav_item_indicators()

    def rename_script_file(self, script_path):
        current_filename = os.path.basename(script_path)
        new_name, ok = QInputDialog.getText(self, "Rename Script", "Enter new filename (must end with .py):", text=current_filename)
        if ok and new_name:
            new_name = new_name.strip()
            if not new_name.endswith(".py"):
                new_name += ".py"
            
            if new_name == current_filename:
                return

            new_path = os.path.join(os.path.dirname(script_path), new_name)
            if os.path.exists(new_path):
                QMessageBox.warning(self, "Error", f"A file named '{new_name}' already exists.")
                return

            try:
                if script_path in self.processes and self.processes[script_path].poll() is None:
                    self.processes[script_path].terminate()
                    del self.processes[script_path]

                os.rename(script_path, new_path)
                self.refresh_modules_from_disk()
                self.update_status_label(f"Renamed to {new_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename file: {e}")

    def toggle_executable(self, script_path):
        try:
            st = os.stat(script_path)
            is_currently_exec = bool(st.st_mode & stat.S_IXUSR)
            
            if is_currently_exec:
                new_mode = st.st_mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH
                os.chmod(script_path, new_mode)
                action_text = "Make Executable"
                status_msg = f"Removed executable permission from {os.path.basename(script_path)}"
                popup_msg = f"'{os.path.basename(script_path)}' is no longer executable."
            else:
                new_mode = st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                os.chmod(script_path, new_mode)
                action_text = "Make Unexecutable"
                status_msg = f"Granted executable permission to {os.path.basename(script_path)}"
                popup_msg = f"'{os.path.basename(script_path)}' is now executable (+x)."

            if script_path in self.chmod_buttons:
                self.chmod_buttons[script_path].setText(action_text)

            for mod in self.modules:
                if mod['path'] == script_path:
                    mod['executable'] = not is_currently_exec
                    break

            self.update_status_label(status_msg)
            QMessageBox.information(self, "Success", popup_msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not change permissions: {e}")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().endswith('.py'):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        added_count = 0
        for url in event.mimeData().urls():
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if file_path.endswith('.py'):
                    filename = os.path.basename(file_path)
                    dest_path = os.path.join(MODULES_DIR, filename)
                    try:
                        shutil.copy(file_path, dest_path)
                        added_count += 1
                    except Exception as e:
                        print(f"Error copying file: {e}")
        
        if added_count > 0:
            self.refresh_modules_from_disk()

    def remove_module(self, script_path):
        mod_name = os.path.basename(script_path)
        confirm = QMessageBox.question(
            self, "Remove Script", 
            f"Are you sure you want to remove '{mod_name}' from the workspace?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                if script_path in self.processes and self.processes[script_path].poll() is None:
                    self.processes[script_path].terminate()
                    del self.processes[script_path]
                
                if os.path.exists(script_path):
                    os.remove(script_path)
                
                self.refresh_modules_from_disk()
            except Exception as e:
                self.update_status_label(f"Error removing script ({e})")

    def switch_view(self, index):
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)

    def launch_external_persistent(self, script_path):
        if os.path.exists(script_path):
            try:
                if script_path in self.processes and self.processes[script_path].poll() is None:
                    self.update_status_label(f"{os.path.basename(script_path)} is already active.")
                else:
                    proc = subprocess.Popen([sys.executable, script_path])
                    
                    if proc.poll() is not None:
                        self.update_status_label(f"Failed to launch {os.path.basename(script_path)}")
                        QMessageBox.critical(self, "Launch Error", f"The script {os.path.basename(script_path)} crashed immediately upon startup.")
                    else:
                        self.processes[script_path] = proc
                        self.update_status_label(f"Successfully launched {os.path.basename(script_path)}")
            except Exception as e:
                self.update_status_label("Error launching script")
                QMessageBox.critical(self, "Launch Error", f"Could not launch script: {e}")
        else:
            self.update_status_label("Error - Script not found.")
            QMessageBox.warning(self, "Missing File", f"The script path {script_path} does not exist.")

    def launch_in_terminal(self, script_path):
        if not os.path.exists(script_path):
            self.update_status_label("Error - Script not found.")
            QMessageBox.warning(self, "Missing File", f"The script path {script_path} does not exist.")
            return

        abs_path = os.path.abspath(script_path)
        
        terminals = [
            ("gnome-terminal", ["gnome-terminal", "--", sys.executable, abs_path]),
            ("konsole", ["konsole", "-e", sys.executable, abs_path]),
            ("xfce4-terminal", ["xfce4-terminal", "-e", f"{sys.executable} {abs_path}"]),
            ("tilix", ["tilix", "-e", f"{sys.executable} {abs_path}"]),
            ("terminator", ["terminator", "-x", sys.executable, abs_path]),
            ("alacritty", ["alacritty", "-e", sys.executable, abs_path]),
            ("kitty", ["kitty", sys.executable, abs_path]),
            ("foot", ["foot", sys.executable, abs_path]),
            ("xterm", ["xterm", "-hold", "-e", f"{sys.executable} {abs_path}"])
        ]

        launched = False
        for term_name, cmd in terminals:
            if shutil.which(term_name):
                try:
                    subprocess.Popen(cmd)
                    self.update_status_label(f"Launched {os.path.basename(script_path)} in {term_name}.")
                    launched = True
                    break
                except Exception as e:
                    print(f"Failed to launch via {term_name}: {e}")

        if not launched:
            QMessageBox.critical(
                self, "Terminal Error", 
                "No supported external Linux terminal emulator found (checked gnome-terminal, konsole, xfce4-terminal, alacritty, kitty, xterm, etc.)."
            )

    def closeEvent(self, event):
        unsaved_paths = [p for p in self.editors if self.has_unsaved_changes(p)]
        
        if unsaved_paths:
            file_names_str = "\n".join([f"• {os.path.basename(p)}" for p in unsaved_paths])
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Unsaved Modifications on Exit")
            msg_box.setText("You have unsaved changes in the following script(s):")
            msg_box.setInformativeText(file_names_str + "\n\nDo you want to save your changes before exiting?")
            
            save_btn = msg_box.addButton("Save All and Exit", QMessageBox.ButtonRole.AcceptRole)
            discard_btn = msg_box.addButton("Exit Without Saving", QMessageBox.ButtonRole.DestructiveRole)
            cancel_btn = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            
            msg_box.exec()
            clicked = msg_box.clickedButton()
            
            if clicked == save_btn:
                try:
                    for p in unsaved_paths:
                        content = self.editors[p].toPlainText()
                        with open(p, 'w', encoding='utf-8') as f:
                            f.write(content)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save files on exit: {e}")
                    event.ignore()
                    return
            elif clicked == cancel_btn:
                event.ignore()
                return

        for script, proc in self.processes.items():
            if proc.poll() is None:
                proc.terminate()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    suite = LinuxPythonLauncherEditor()
    suite.show()
    sys.exit(app.exec())