#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Dynamic Linux Productivity Suite Launcher with Drag-and-Drop, Editor, and Cancel Support
# Copyright (C) 2026 brunonlinespace
#

import os
import sys
import shutil
import subprocess
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QListWidget, QMessageBox, QTextEdit
)

# Internal directory where dropped plug-and-play python scripts are stored automatically
MODULES_DIR = "modules"

class DynamicProductivitySuite(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dynamic Linux Productivity Suite with Editor")
        self.resize(1300, 850)

        # Enable drop events on the main application window
        self.setAcceptDrops(True)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Active processes tracking
        self.processes = {}

        # Discover available scripts dynamically
        self.modules = self.discover_modules()

        # Build UI components
        self.setup_sidebar()
        self.setup_content_area()

    def discover_modules(self):
        """Scans the modules directory for python scripts and returns a list of dictionaries."""
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

        title_lbl = QLabel("<h3>🛠️ Suite Control</h3>")
        sidebar_layout.addWidget(title_lbl)

        info_drop_lbl = QLabel("<font color='#9cdcfe'>💡 Tip: Drag & drop .py scripts anywhere onto the app to add them!</font>")
        info_drop_lbl.setWordWrap(True)
        info_drop_lbl.setStyleSheet("font-size: 8.5pt; margin-bottom: 5px;")
        sidebar_layout.addWidget(info_drop_lbl)

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

        self.status_lbl = QLabel(f"Status: Loaded {len(self.modules)} modules.")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet("color: #9cdcfe; font-size: 9pt;")
        sidebar_layout.addWidget(self.status_lbl)

        self.main_layout.addWidget(sidebar)

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

    def refresh_content_pages(self):
        while self.stack.count() > 0:
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
            widget.deleteLater()

        # Page 0: Dynamic Dashboard Home
        dash_widget = QWidget()
        dash_layout = QVBoxLayout(dash_widget)
        dash_layout.setContentsMargins(30, 30, 30, 30)
        
        dash_layout.addWidget(QLabel("<h1>Welcome to the Linux Productivity Suite</h1>"))
        dash_layout.addWidget(QLabel("<b>Drag and drop any Python (.py) script file directly onto this window</b> to plug it into the suite automatically."))
        
        self.links_layout = QVBoxLayout()
        self.links_layout.setSpacing(10)
        
        if not self.modules:
            no_mod_lbl = QLabel("<i>No modules found. Drag and drop python scripts here to get started!</i>")
            no_mod_lbl.setStyleSheet("color: #d16969; margin-top: 15px;")
            self.links_layout.addWidget(no_mod_lbl)
        else:
            for index, mod in enumerate(self.modules, start=1):
                btn = QPushButton(f"▶  Launch {mod['name']} ({mod['filename']})")
                btn.setStyleSheet("text-align: left; padding: 10px; font-size: 11pt;")
                btn.clicked.connect(lambda checked, path=mod['path'], idx=index: self.launch_and_switch(path, idx))
                self.links_layout.addWidget(btn)

        dash_layout.addLayout(self.links_layout)
        dash_layout.addStretch()
        self.stack.addWidget(dash_widget)

        # Pages 1-N: Module Management & Live Code Editor Page
        for index, mod in enumerate(self.modules, start=1):
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(20, 20, 20, 20)
            
            # Header info & Control Actions
            header_layout = QHBoxLayout()
            title_info = QLabel(f"<h2>{mod['name']}</h2><font color='#858585'>{mod['path']}</font>")
            
            action_btn = QPushButton("▶ Launch Process")
            action_btn.setStyleSheet("padding: 8px 15px; font-weight: bold; background-color: #007acc; color: white; border: none; border-radius: 4px;")
            action_btn.clicked.connect(lambda checked, path=mod['path']: self.launch_external_persistent(path))
            
            del_btn = QPushButton("Remove")
            del_btn.setStyleSheet("padding: 8px 15px; background-color: #511; color: #f88; border: none; border-radius: 4px;")
            del_btn.clicked.connect(lambda checked, path=mod['path']: self.remove_module(path))

            header_layout.addWidget(title_info)
            header_layout.addStretch()
            header_layout.addWidget(action_btn)
            header_layout.addWidget(del_btn)
            layout.addLayout(header_layout)

            # Integrated Code Editor for this Module Script
            editor_label = QLabel("<b>Embedded Script Editor:</b>")
            editor_label.setStyleSheet("margin-top: 10px;")
            layout.addWidget(editor_label)

            text_editor = QTextEdit()
            text_editor.setFont(QFont("Courier New", 10))
            text_editor.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; border: 1px solid #3f3f46; border-radius: 4px;")
            
            # Load file content into editor
            self.load_editor_content(mod['path'], text_editor)
            layout.addWidget(text_editor)

            # Editor Actions Layout (Cancel & Save buttons)
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
            current_row = self.nav_list.currentRow()
            self.modules = self.discover_modules()
            self.populate_nav_list()
            self.refresh_content_pages()
            self.nav_list.setCurrentRow(min(current_row, self.nav_list.count() - 1))
            self.status_lbl.setText(f"Status: Successfully added {added_count} new module(s).")

    def remove_module(self, script_path):
        mod_name = os.path.basename(script_path)
        confirm = QMessageBox.question(
            self, "Remove Module", 
            f"Are you sure you want to remove '{mod_name}' from the suite?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                if script_path in self.processes and self.processes[script_path].poll() is None:
                    self.processes[script_path].terminate()
                    del self.processes[script_path]
                
                if os.path.exists(script_path):
                    os.remove(script_path)
                
                self.modules = self.discover_modules()
                self.populate_nav_list()
                self.refresh_content_pages()
                self.nav_list.setCurrentRow(0)
                self.status_lbl.setText(f"Status: Removed module {mod_name}")
            except Exception as e:
                self.status_lbl.setText(f"Status: Error removing module ({e})")

    def switch_view(self, index):
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)

    def launch_and_switch(self, script_path, target_index):
        self.launch_external_persistent(script_path)
        self.switch_view(target_index)

    def launch_external_persistent(self, script_path):
        if os.path.exists(script_path):
            try:
                if script_path in self.processes and self.processes[script_path].poll() is None:
                    self.status_lbl.setText(f"Status: {os.path.basename(script_path)} is already active.")
                else:
                    proc = subprocess.Popen([sys.executable, script_path])
                    self.processes[script_path] = proc
                    self.status_lbl.setText(f"Status: Successfully launched {os.path.basename(script_path)}")
            except Exception as e:
                self.status_lbl.setText(f"Status: Error launching script ({e})")
        else:
            self.status_lbl.setText(f"Status: Error - {script_path} not found.")

    def closeEvent(self, event):
        for script, proc in self.processes.items():
            if proc.poll() is None:
                proc.terminate()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    suite = DynamicProductivitySuite()
    suite.show()
    sys.exit(app.exec())
