#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Drag-and-Drop Modular Productivity Suite Launcher
# Copyright (C) 2026 AI Collaborator / brunonlinespace
#

import os
import sys
import subprocess
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDrag, QCursor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QListWidget, QGridLayout
)

MODULES_DIR = "modules"

class DraggablePluginCard(QFrame):
    """An interactive card representing a plugin that can be dragged around."""
    def __init__(self, mod_info, launch_callback, terminate_callback):
        super().__init__()
        self.mod_info = mod_info
        self.launch_callback = launch_callback
        self.terminate_callback = terminate_callback
        
        self.setFixedSize(260, 160)
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #3f3f46;
                border-radius: 8px;
            }
            QFrame:hover {
                border: 1px solid #007acc;
                background-color: #333337;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        # Title
        title_lbl = QLabel(f"<b>📦 {mod_info['name']}</b>")
        title_lbl.setStyleSheet("color: #ffffff; font-size: 11pt; border: none; background: transparent;")
        layout.addWidget(title_lbl)

        # File info
        file_lbl = QLabel(f"<font color='#858585'>File: {mod_info['filename']}</font>")
        file_lbl.setStyleSheet("border: none; background: transparent; font-size: 9pt;")
        layout.addWidget(file_lbl)

        layout.addStretch()

        # Action buttons layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self.launch_btn = QPushButton("Launch")
        self.launch_btn.setStyleSheet("background-color: #007acc; color: white; border: none; padding: 6px; border-radius: 4px; font-weight: bold;")
        self.launch_btn.clicked.connect(lambda: self.launch_callback(mod_info['path']))
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet("background-color: #511; color: #f88; border: none; padding: 6px; border-radius: 4px;")
        self.stop_btn.clicked.connect(lambda: self.terminate_callback(mod_info['path']))

        btn_layout.addWidget(self.launch_btn)
        btn_layout.addWidget(self.stop_btn)
        layout.addLayout(btn_layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.mod_info['filename'])
            drag.setMimeData(mime_data)
            
            # Visual feedback during drag
            drag.exec(Qt.DropAction.MoveAction)


class DropZoneGrid(QGridLayout):
    """A grid layout area that accepts rearranged plugin cards via drag and drop."""
    def __init__(self):
        super().__init__()
        self.setSpacing(15)
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

    def add_widget_to_grid(self, widget, index):
        row = index // 3
        col = index % 3
        self.addWidget(widget, row, col)


class DragDropProductivitySuite(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modular Productivity Suite - Plugin Manager")
        self.resize(1200, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.processes = {}
        self.modules = self.discover_modules()

        self.setup_sidebar()
        self.setup_content_area()

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
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("background-color: #252526; color: #ffffff;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)

        title_lbl = QLabel("<h3>🛠️ Suite Control</h3>")
        sidebar_layout.addWidget(title_lbl)

        self.nav_list = QListWidget()
        self.nav_list.setStyleSheet("""
            QListWidget { background-color: #252526; border: none; color: #dcdcdc; font-size: 11pt; }
            QListWidget::item { padding: 10px; border-radius: 4px; margin-bottom: 4px; }
            QListWidget::item:selected { background-color: #007acc; color: #ffffff; font-weight: bold; }
            QListWidget::item:hover:!selected { background-color: #3e3e42; }
        """)
        
        # Sidebar now contains a single clean navigation target
        self.nav_list.addItem("🧩 Plugin Dashboard")
        self.nav_list.currentRowChanged.connect(self.switch_view)
        sidebar_layout.addWidget(self.nav_list)
        sidebar_layout.addStretch()

        self.status_lbl = QLabel(f"Status: Found {len(self.modules)} plugins.")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet("color: #9cdcfe; font-size: 9pt;")
        sidebar_layout.addWidget(self.status_lbl)

        self.main_layout.addWidget(sidebar)

    def setup_content_area(self):
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)

        # Single Unified Dashboard View
        dash_widget = QWidget()
        dash_widget.setAcceptDrops(True)
        dash_layout = QVBoxLayout(dash_widget)
        dash_layout.setContentsMargins(30, 30, 30, 30)
        
        dash_layout.addWidget(QLabel("<h1>Modular Plugin Manager</h1>"))
        dash_layout.addWidget(QLabel(f"Drag and drop plugin cards to organize your workspace. Drop python files into <b>'{MODULES_DIR}/'</b> to expand dynamically."))
        
        # Grid container for plugin cards
        self.grid_container = QWidget()
        self.grid_layout = DropZoneGrid()
        self.grid_container.setLayout(self.grid_layout)

        if not self.modules:
            no_mod_lbl = QLabel(f"<i>No python scripts found in '{MODULES_DIR}/'.</i>")
            no_mod_lbl.setStyleSheet("color: #d16969; margin-top: 15px;")
            dash_layout.addWidget(no_mod_lbl)
        else:
            for index, mod in enumerate(self.modules):
                card = DraggablePluginCard(
                    mod, 
                    self.launch_external_persistent, 
                    self.terminate_external
                )
                self.grid_layout.add_widget_to_grid(card, index)

        dash_layout.addWidget(self.grid_container)
        dash_layout.addStretch()
        
        self.stack.addWidget(dash_widget)
        self.nav_list.setCurrentRow(0)

    def switch_view(self, index):
        self.stack.setCurrentIndex(index)

    def launch_external_persistent(self, script_path):
        if os.path.exists(script_path):
            try:
                if script_path in self.processes and self.processes[script_path].poll() is None:
                    self.status_lbl.setText(f"Status: {os.path.basename(script_path)} is already running.")
                else:
                    proc = subprocess.Popen([sys.executable, script_path])
                    self.processes[script_path] = proc
                    self.status_lbl.setText(f"Status: Launched {os.path.basename(script_path)}")
            except Exception as e:
                self.status_lbl.setText(f"Status: Error ({e})")
        else:
            self.status_lbl.setText(f"Status: Error - Script missing.")

    def terminate_external(self, script_path):
        if script_path in self.processes and self.processes[script_path].poll() is None:
            self.processes[script_path].terminate()
            self.status_lbl.setText(f"Status: Stopped {os.path.basename(script_path)}")
        else:
            self.status_lbl.setText(f"Status: Plugin is not active.")

    def closeEvent(self, event):
        for script, proc in self.processes.items():
            if proc.poll() is None:
                proc.terminate()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    suite = DragDropProductivitySuite()
    suite.show()
    sys.exit(app.exec())