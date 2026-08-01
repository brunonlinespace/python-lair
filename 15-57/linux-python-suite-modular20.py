#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Linux Python Launcher & Editor with Responsive Grid Layout & State Memory
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
# Version: 20

import os
import sys
import json
import stat
import shutil
import subprocess
from PyQt6.QtCore import Qt, QUrl, QRect, QSize, QPoint
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QListWidget, QMessageBox, QTextEdit, QScrollArea, QLayout, QInputDialog
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


class LinuxPythonLauncherEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Linux Python Launcher & Editor")
        self.resize(1350, 850)

        self.setAcceptDrops(True)

        self.dashboard_mode = self.load_dashboard_state()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.processes = {}
        self.modules = self.discover_modules()

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
            
        for filename in sorted(os.listdir(MODULES_DIR)):
            if filename.endswith(".py") and filename != "__init__.py":
                script_path = os.path.join(MODULES_DIR, filename)
                display_name = filename[:-3].replace("-", " ").replace("_", " ").title()
                
                modules_list.append({
                    "name": display_name,
                    "filename": filename,
                    "path": script_path
                })
        return modules_list

    def setup_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet("background-color: #252526; color: #ffffff;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)

        title_lbl = QLabel("<h3>🛠️ Workspace Control</h3>")
        sidebar_layout.addWidget(title_lbl)

        info_drop_lbl = QLabel("<font color='#9cdcfe'>💡 Tip: Drag & drop .py scripts anywhere onto the app to add them!</font>")
        info_drop_lbl.setWordWrap(True)
        info_drop_lbl.setStyleSheet("font-size: 8.5pt; margin-bottom: 5px;")
        sidebar_layout.addWidget(info_drop_lbl)

        refresh_btn = QPushButton("🔄 Refresh Modules")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #333337; color: #dcdcdc; border: 1px solid #555; 
                border-radius: 4px; padding: 6px; font-weight: bold; margin-bottom: 5px;
            }
            QPushButton:hover {
                background-color: #3e3e42; border-color: #007acc;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_modules_from_disk)
        sidebar_layout.addWidget(refresh_btn)

        self.nav_list = QListWidget()
        self.nav_list.setStyleSheet("""
            QListWidget { background-color: #252526; border: none; color: #dcdcdc; font-size: 11pt; }
            QListWidget::item { padding: 10px; border-radius: 4px; margin-bottom: 4px; }
            QListWidget::item:selected { background-color: #007acc; color: #ffffff; font-weight: bold; }
            QListWidget::item:hover:!selected { background-color: #3e3e42; }
        """)
        
        self.populate_nav_list()
        self.nav_list.currentRowChanged.connect(self.switch_view)
        sidebar_layout.addWidget(self.nav_list)
        sidebar_layout.addStretch()

        self.status_lbl = QLabel(f"Status: Loaded {len(self.modules)} scripts.")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet("color: #9cdcfe; font-size: 9pt;")
        sidebar_layout.addWidget(self.status_lbl)

        self.main_layout.addWidget(sidebar)

    def refresh_modules_from_disk(self):
        current_row = self.nav_list.currentRow()
        old_count = len(self.modules)
        
        self.modules = self.discover_modules()
        self.populate_nav_list()
        self.refresh_content_pages()
        
        self.nav_list.setCurrentRow(min(current_row, self.nav_list.count() - 1))
        
        new_count = len(self.modules)
        diff = new_count - old_count
        
        if diff > 0:
            msg = f"Refreshed: Found {diff} new script(s)."
        elif diff < 0:
            msg = f"Refreshed: {abs(diff)} script(s) removed."
        else:
            msg = "Refreshed: Modules folder is up to date."
            
        self.status_lbl.setText(f"Status: {msg}")

    def populate_nav_list(self):
        self.nav_list.clear()
        self.nav_list.addItem("🏠 Dashboard")
        for mod in self.modules:
            self.nav_list.addItem(f"📦 {mod['name']}")

    def setup_content_area(self):
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)

        self.refresh_content_pages()
        self.nav_list.setCurrentRow(0)

    def toggle_dashboard_mode(self):
        if self.dashboard_mode == "list":
            self.dashboard_mode = "grid"
        else:
            self.dashboard_mode = "list"
        
        self.save_dashboard_state()
        self.refresh_content_pages()
        self.nav_list.setCurrentRow(0)

    def refresh_content_pages(self):
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

        desc_label = QLabel("<b>Drag and drop any Python (.py) script file directly onto this window</b> or edit files externally in the <b>modules/</b> folder, then click <b>Refresh Modules</b>.")
        desc_label.setWordWrap(True)
        dash_layout.addWidget(desc_label)

        # View switch control moved right above the scripts list area to prevent squashing
        controls_row = QHBoxLayout()
        controls_row.setContentsMargins(0, 10, 0, 5)
        
        section_lbl = QLabel("<b>Installed Scripts / Modules</b>")
        section_lbl.setStyleSheet("font-size: 11pt; color: #dcdcdc;")
        controls_row.addWidget(section_lbl)
        controls_row.addStretch()

        mode_btn_text = "🔲 Switch to Grid View" if self.dashboard_mode == "list" else "📋 Switch to List View"
        self.mode_toggle_btn = QPushButton(mode_btn_text)
        self.mode_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #333337; color: #ffffff; border: 1px solid #555;
                border-radius: 4px; padding: 6px 12px; font-weight: bold; font-size: 9.5pt;
            }
            QPushButton:hover {
                background-color: #007acc; border-color: #007acc;
            }
        """)
        self.mode_toggle_btn.clicked.connect(self.toggle_dashboard_mode)
        controls_row.addWidget(self.mode_toggle_btn)
        dash_layout.addLayout(controls_row)
        
        if not self.modules:
            no_mod_lbl = QLabel("<i>No python scripts found. Add scripts to the modules folder or drop them here!</i>")
            no_mod_lbl.setWordWrap(True)
            no_mod_lbl.setStyleSheet("color: #d16969; margin-top: 15px;")
            dash_layout.addWidget(no_mod_lbl)
        else:
            if self.dashboard_mode == "list":
                self.links_layout = QVBoxLayout()
                self.links_layout.setSpacing(12)

                for index, mod in enumerate(self.modules, start=1):
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
                    
                    info_lbl = QLabel(f"<span style='color: #ffffff; font-size: 11pt;'><b>{mod['name']}</b></span><br><span style='color: #858585; font-size: 9pt;'>{mod['filename']}</span>")
                    info_lbl.setWordWrap(True)
                    info_lbl.setStyleSheet("border: none; background: transparent;")
                    
                    btn_layout = QHBoxLayout()
                    btn_layout.setSpacing(8)

                    launch_btn = QPushButton("▶ Launch")
                    launch_btn.setToolTip("Run script in standard background process")
                    launch_btn.setStyleSheet("background-color: #007acc; color: white; border: none; padding: 6px 10px; border-radius: 4px; font-weight: bold;")
                    launch_btn.clicked.connect(lambda checked, path=mod['path']: self.launch_external_persistent(path))

                    term_btn = QPushButton("🖥 Terminal")
                    term_btn.setToolTip("Launch TUI / script in an external interactive terminal emulator")
                    term_btn.setStyleSheet("background-color: #2d5a2d; color: #cfc; border: none; padding: 6px 10px; border-radius: 4px; font-weight: bold;")
                    term_btn.clicked.connect(lambda checked, path=mod['path']: self.launch_in_terminal(path))

                    edit_btn = QPushButton("✏ Edit")
                    edit_btn.setStyleSheet("background-color: #333337; color: #dcdcdc; border: 1px solid #555; border-radius: 4px; padding: 6px 10px;")
                    edit_btn.clicked.connect(lambda checked, idx=index: self.nav_list.setCurrentRow(idx))

                    del_btn = QPushButton("🗑 Remove")
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
                # --- RESPONSIVE FLOW GRID LAYOUT ---
                self.flow_layout = FlowLayout(margin=0, spacing=15)

                for index, mod in enumerate(self.modules, start=1):
                    card_frame = QFrame()
                    card_frame.setFixedSize(310, 175)
                    card_frame.setStyleSheet("""
                        QFrame {
                            background-color: #1e1e1e;
                            border: 1px solid #333338;
                            border-radius: 8px;
                        }
                        QFrame:hover {
                            border: 1px solid #007acc;
                            background-color: #252526;
                        }
                    """)
                    grid_card_layout = QVBoxLayout(card_frame)
                    grid_card_layout.setContentsMargins(12, 12, 12, 12)

                    title_lbl = QLabel(f"<b>📦 {mod['name']}</b>")
                    title_lbl.setStyleSheet("color: #ffffff; font-size: 11pt; border: none; background: transparent;")
                    title_lbl.setWordWrap(True)
                    grid_card_layout.addWidget(title_lbl)

                    file_lbl = QLabel(f"<font color='#858585'>File: {mod['filename']}</font>")
                    file_lbl.setStyleSheet("border: none; background: transparent; font-size: 9pt;")
                    grid_card_layout.addWidget(file_lbl)

                    grid_card_layout.addStretch()

                    grid_btn_layout = QHBoxLayout()
                    grid_btn_layout.setSpacing(4)

                    launch_btn = QPushButton("Launch")
                    launch_btn.setToolTip("Run background process")
                    launch_btn.setStyleSheet("background-color: #007acc; color: white; border: none; padding: 6px 8px; border-radius: 4px; font-weight: bold; font-size: 9pt;")
                    launch_btn.clicked.connect(lambda checked, path=mod['path']: self.launch_external_persistent(path))

                    term_btn = QPushButton("Terminal")
                    term_btn.setToolTip("Launch TUI in terminal window")
                    term_btn.setStyleSheet("background-color: #2d5a2d; color: #cfc; border: none; padding: 6px 8px; border-radius: 4px; font-weight: bold; font-size: 9pt;")
                    term_btn.clicked.connect(lambda checked, path=mod['path']: self.launch_in_terminal(path))

                    edit_btn = QPushButton("Edit")
                    edit_btn.setStyleSheet("background-color: #333337; color: #dcdcdc; border: 1px solid #555; border-radius: 4px; padding: 6px 8px; font-size: 9pt;")
                    edit_btn.clicked.connect(lambda checked, idx=index: self.nav_list.setCurrentRow(idx))

                    del_btn = QPushButton("Del")
                    del_btn.setStyleSheet("background-color: #511; color: #f88; border: none; padding: 6px 8px; border-radius: 4px; font-size: 9pt;")
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

        # Pages 1-N: Script Editor Pages
        for index, mod in enumerate(self.modules, start=1):
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(20, 20, 20, 20)
            
            title_info = QLabel(f"<h2>{mod['name']}</h2><font color='#858585'>{mod['path']}</font>")
            title_info.setWordWrap(True)
            layout.addWidget(title_info)

            btn_row = QHBoxLayout()
            btn_row.setSpacing(8)
            
            action_btn = QPushButton("▶ Launch")
            action_btn.setStyleSheet("padding: 8px 12px; font-weight: bold; background-color: #007acc; color: white; border: none; border-radius: 4px;")
            action_btn.clicked.connect(lambda checked, path=mod['path']: self.launch_external_persistent(path))

            term_action_btn = QPushButton("🖥 Terminal")
            term_action_btn.setStyleSheet("padding: 8px 12px; font-weight: bold; background-color: #2d5a2d; color: #cfc; border: none; border-radius: 4px;")
            term_action_btn.clicked.connect(lambda checked, path=mod['path']: self.launch_in_terminal(path))

            rename_btn = QPushButton("✏ Rename")
            rename_btn.setStyleSheet("padding: 8px 12px; background-color: #333337; color: #dcdcdc; border: 1px solid #555; border-radius: 4px;")
            rename_btn.clicked.connect(lambda checked, path=mod['path']: self.rename_script_file(path))

            chmod_btn = QPushButton("⚙ +x Executable")
            chmod_btn.setStyleSheet("padding: 8px 12px; background-color: #333337; color: #dcdcdc; border: 1px solid #555; border-radius: 4px;")
            chmod_btn.clicked.connect(lambda checked, path=mod['path']: self.make_executable(path))
            
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

            text_editor = QTextEdit()
            text_editor.setFont(QFont("Courier New", 10))
            text_editor.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; border: 1px solid #3f3f46; border-radius: 4px;")
            
            self.load_editor_content(mod['path'], text_editor)
            layout.addWidget(text_editor)

            editor_btn_layout = QHBoxLayout()
            editor_btn_layout.addStretch()

            cancel_btn = QPushButton("↩ Cancel Changes")
            cancel_btn.setFixedWidth(150)
            cancel_btn.setStyleSheet("padding: 8px; background-color: #333337; color: #ccc; border: 1px solid #555; border-radius: 4px;")
            cancel_btn.clicked.connect(lambda checked, p=mod['path'], ed=text_editor: self.reload_module_code(p, ed))

            save_btn = QPushButton("💾 Save Script Changes")
            save_btn.setFixedWidth(180)
            save_btn.setStyleSheet("padding: 8px; background-color: #285228; color: #cfc; border: none; border-radius: 4px; font-weight: bold;")
            save_btn.clicked.connect(lambda checked, p=mod['path'], ed=text_editor: self.save_module_code(p, ed))
            
            editor_btn_layout.addWidget(cancel_btn)
            editor_btn_layout.addWidget(save_btn)
            layout.addLayout(editor_btn_layout)

            self.stack.addWidget(page)

    def load_editor_content(self, script_path, editor):
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                editor.setPlainText(f.read())
        except Exception as e:
            editor.setPlainText(f"# Error loading file content: {e}")

    def reload_module_code(self, script_path, editor):
        confirm = QMessageBox.question(
            self, "Discard Changes", 
            "Are you sure you want to discard your unsaved changes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.load_editor_content(script_path, editor)
            self.status_lbl.setText(f"Status: Discarded changes for {os.path.basename(script_path)}")

    def save_module_code(self, script_path, editor):
        try:
            content = editor.toPlainText()
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.status_lbl.setText(f"Status: Successfully saved changes to {os.path.basename(script_path)}")
            QMessageBox.information(self, "Success", f"Changes to {os.path.basename(script_path)} saved successfully!")
        except Exception as e:
            self.status_lbl.setText(f"Status: Error saving file ({e})")
            QMessageBox.critical(self, "Error", f"Could not save file: {e}")

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
                self.status_lbl.setText(f"Status: Renamed to {new_name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not rename file: {e}")

    def make_executable(self, script_path):
        try:
            st = os.stat(script_path)
            os.chmod(script_path, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            self.status_lbl.setText(f"Status: Granted executable permission to {os.path.basename(script_path)}")
            QMessageBox.information(self, "Success", f"'{os.path.basename(script_path)}' is now executable (+x).")
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
                self.status_lbl.setText(f"Status: Error removing script ({e})")

    def switch_view(self, index):
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)

    def launch_external_persistent(self, script_path):
        if os.path.exists(script_path):
            try:
                if script_path in self.processes and self.processes[script_path].poll() is None:
                    self.status_lbl.setText(f"Status: {os.path.basename(script_path)} is already active.")
                else:
                    proc = subprocess.Popen([sys.executable, script_path])
                    
                    if proc.poll() is not None:
                        self.status_lbl.setText(f"Status: Failed to launch {os.path.basename(script_path)}")
                        QMessageBox.critical(self, "Launch Error", f"The script {os.path.basename(script_path)} crashed immediately upon startup.")
                    else:
                        self.processes[script_path] = proc
                        self.status_lbl.setText(f"Status: Successfully launched {os.path.basename(script_path)}")
            except Exception as e:
                self.status_lbl.setText(f"Status: Error launching script")
                QMessageBox.critical(self, "Launch Error", f"Could not launch script: {e}")
        else:
            self.status_lbl.setText(f"Status: Error - Script not found.")
            QMessageBox.warning(self, "Missing File", f"The script path {script_path} does not exist.")

    def launch_in_terminal(self, script_path):
        """Automatically detects available Linux terminal emulators to run interactive TUI scripts."""
        if not os.path.exists(script_path):
            self.status_lbl.setText("Status: Error - Script not found.")
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
                    self.status_lbl.setText(f"Status: Launched {os.path.basename(script_path)} in {term_name}.")
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
        for script, proc in self.processes.items():
            if proc.poll() is None:
                proc.terminate()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    suite = LinuxPythonLauncherEditor()
    suite.show()
    sys.exit(app.exec())