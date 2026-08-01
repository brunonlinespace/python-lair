#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Dynamic Linux Productivity Suite Launcher
# Copyright (C) 2026 AI Collaborator / brunonlinespace
#

import os
import sys
import subprocess
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QListWidget
)

# Directory where individual plug-and-play python scripts will reside
MODULES_DIR = "modules"

class DynamicProductivitySuite(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dynamic Linux Productivity Suite")
        self.resize(1200, 800)

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
        
        # Ensure the modules directory exists
        if not os.path.exists(MODULES_DIR):
            os.makedirs(MODULES_DIR)
            
        # Look for .py files inside the modules folder
        for filename in sorted(os.listdir(MODULES_DIR)):
            if filename.endswith(".py") and filename != "__init__.py":
                script_path = os.path.join(MODULES_DIR, filename)
                # Pretty format name (e.g., "linux-resmon.py" -> "Linux Resmon")
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
        
        # Index 0 is always the dynamic home Dashboard
        self.nav_list.addItem("🏠 Dashboard")

        # Dynamically add sidebar items for every detected module script
        for mod in self.modules:
            self.nav_list.addItem(f"📦 {mod['name']}")
        
        self.nav_list.currentRowChanged.connect(self.switch_view)
        sidebar_layout.addWidget(self.nav_list)
        sidebar_layout.addStretch()

        self.status_lbl = QLabel(f"Status: Loaded {len(self.modules)} modules.")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet("color: #9cdcfe; font-size: 9pt;")
        sidebar_layout.addWidget(self.status_lbl)

        self.main_layout.addWidget(sidebar)

    def setup_content_area(self):
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)

        # Page 0: Dynamic Dashboard Home
        dash_widget = QWidget()
        dash_layout = QVBoxLayout(dash_widget)
        dash_layout.setContentsMargins(30, 30, 30, 30)
        
        dash_layout.addWidget(QLabel("<h1>Welcome to the Linux Productivity Suite</h1>"))
        dash_layout.addWidget(QLabel(f"Plug scripts into the <b>'{MODULES_DIR}/'</b> directory to load them dynamically."))
        
        # Quick action links container
        self.links_layout = QVBoxLayout()
        self.links_layout.setSpacing(10)
        
        if not self.modules:
            no_mod_lbl = QLabel(f"<i>No python scripts found in '{MODULES_DIR}/'. Add some to get started!</i>")
            no_mod_lbl.setStyleSheet("color: #d16969; margin-top: 15px;")
            self.links_layout.addWidget(no_mod_lbl)
        else:
            # Generate quick action cards/buttons for each discovered script
            for index, mod in enumerate(self.modules, start=1):
                btn = QPushButton(f"▶  Launch {mod['name']} ({mod['filename']})")
                btn.setStyleSheet("text-align: left; padding: 10px; font-size: 11pt;")
                btn.clicked.connect(lambda checked, path=mod['path'], idx=index: self.launch_and_switch(path, idx))
                self.links_layout.addWidget(btn)

        dash_layout.addLayout(self.links_layout)
        dash_layout.addStretch()
        self.stack.addWidget(dash_widget)

        # Pages 1-N: Dynamic individual panes for each discovered module
        for index, mod in enumerate(self.modules, start=1):
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            lbl = QLabel(f"<h2>{mod['name']}</h2><p>File: <code>{mod['path']}</code></p><p>Click below to open or restart this plugin instance safely.</p>")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            action_btn = QPushButton(f"Open {mod['name']}")
            action_btn.setFixedWidth(220)
            action_btn.setStyleSheet("padding: 8px; font-weight: bold;")
            action_btn.clicked.connect(lambda checked, path=mod['path']: self.launch_external_persistent(path))
            
            layout.addWidget(lbl)
            layout.addWidget(action_btn, alignment=Qt.AlignmentFlag.AlignCenter)
            self.stack.addWidget(page)

        self.nav_list.setCurrentRow(0)

    def switch_view(self, index):
        self.stack.setCurrentIndex(index)

    def launch_and_switch(self, script_path, target_index):
        self.launch_external_persistent(script_path)
        self.nav_list.setCurrentRow(target_index)

    def launch_external_persistent(self, script_path):
        if os.path.exists(script_path):
            try:
                # Check if an existing process for this script is already running
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