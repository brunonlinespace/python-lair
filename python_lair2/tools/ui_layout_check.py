#!/usr/bin/env python3
# Python Lair 2
# SPDX-License-Identifier: GPL-3.0-or-later
"""Static checks for the pure-PyQt experimental UI layout."""

from pathlib import Path


def main() -> int:
    package = Path(__file__).resolve().parents[1]
    dashboard = (package / "widgets/dashboard.py").read_text(encoding="utf-8")
    navigation = (package / "widgets/navigation.py").read_text(encoding="utf-8")
    editor_page = (package / "widgets/editor_page.py").read_text(encoding="utf-8")
    main_window = (package / "widgets/main_window.py").read_text(encoding="utf-8")

    stack_start = dashboard.index("    def viewport_width_hint")
    stack_end = dashboard.index("    def _current_page_changed", stack_start)
    stack_method = dashboard[stack_start:stack_end]

    required = (
        (stack_method, "while ancestor is not None"),
        (stack_method, "isinstance(ancestor, QScrollArea)"),
        (stack_method, "return 800"),
        (dashboard, "minimum_width=132"),
        (dashboard, "self.sort_combo.setMaximumWidth(150)"),
        (navigation, "self.workspace_label.setAlignment("),
        (navigation, "Qt.AlignmentFlag.AlignCenter"),
        (navigation, "layout.addSpacing(18)"),
    )
    main_source = (package.parent / "main.py").read_text(encoding="utf-8")
    widget_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((package / "widgets").glob("*.py"))
    )

    forbidden = (
        (stack_method, "self.sizeHint()"),
        (navigation, "dashboard-24.png"),
        (widget_sources, "setStyleSheet("),
        (widget_sources, "style='"),
        (main_source, 'app.setStyle("Fusion")'),
        (main_source, "app.setPalette("),
        (navigation, "self.tree.setItemDelegate(NavigationItemDelegate"),
    )

    dashboard_position = navigation.index("self.dashboard_button = DashboardNavigationButton")
    workspace_position = navigation.index("self.workspace_label = QLabel")
    if dashboard_position >= workspace_position:
        raise SystemExit("Dashboard must appear above Workspace in the sidebar.")

    editor_required = (
        'self.editor_file_menu = QMenu("File", self)',
        'self.editor_edit_menu = QMenu("Edit", self)',
        'self.editor_view_menu = QMenu("View", self)',
        'self.editor_run_menu = QMenu("Run", self)',
        'self.launch_button = QPushButton("Launch")',
        'self.terminal_button = QPushButton("In Terminal")',
        'self.admin_button = QPushButton("As Admin")',
        'self.stop_button = QPushButton("Stop")',
        'self.force_stop_button = QPushButton("Force Stop")',
        'self.executable_button = QPushButton("Make Exec")',
        'self.cancel_changes_button = QPushButton("Cancel Changes")',
        'self.save_changes_button = QPushButton("Save Changes")',
    )
    forbidden_editor_button_layer = (
        'self.editor_file_button = QPushButton("File")',
        'self.editor_edit_button = QPushButton("Edit")',
        'self.editor_view_button = QPushButton("View")',
        'self.editor_run_button = QPushButton("Run")',
        "self.editor_menu_row",
    )
    remaining_editor_button_layer = [
        item for item in forbidden_editor_button_layer if item in editor_page
    ]
    if remaining_editor_button_layer:
        raise SystemExit(
            "Obsolete embedded File/Edit/View/Run button layer remains: "
            f"{remaining_editor_button_layer}"
        )

    missing_editor = [item for item in editor_required if item not in editor_page]
    if missing_editor:
        raise SystemExit(f"Missing embedded-editor menu wiring: {missing_editor}")
    restored_editor_controls = (
        'QPushButton("Launch")',
        'QPushButton("In Terminal")',
        'QPushButton("As Admin")',
        'QPushButton("Make Exec")',
        'QPushButton("Cancel Changes")',
        'QPushButton("Save Changes")',
        'self.editor_action_separator.setFrameShape(QFrame.Shape.VLine)',
    )
    missing_restored = [
        item for item in restored_editor_controls if item not in editor_page
    ]
    if missing_restored:
        raise SystemExit(
            f"Missing restored embedded-editor action controls: {missing_restored}"
        )
    obsolete_editor_controls = (
        "self.find_button",
        "self.replace_button",
        "self.replace_all_button",
        "self.goto_button",
    )
    remaining = [item for item in obsolete_editor_controls if item in editor_page]
    if remaining:
        raise SystemExit(
            f"Obsolete embedded-editor search command buttons remain: {remaining}"
        )

    action_order = (
        'QPushButton("Launch")',
        'QPushButton("In Terminal")',
        'QPushButton("As Admin")',
        'QPushButton("Make Exec")',
        'QPushButton("Cancel Changes")',
        'QPushButton("Save Changes")',
    )
    positions = [editor_page.index(item) for item in action_order]
    if positions != sorted(positions):
        raise SystemExit("Restored embedded-editor action order is incorrect.")

    missing = [fragment for source, fragment in required if fragment not in source]
    bad = [fragment for source, fragment in forbidden if fragment in source]
    if missing:
        raise SystemExit(f"Missing UI layout wiring: {missing}")
    if bad:
        raise SystemExit(f"Legacy UI layout wiring remains: {bad}")


    required_navigation = (
        'class NavigationWidget(QFrame)',
        'self.setFrameShape(QFrame.Shape.StyledPanel)',
        'QLabel("<h3>My Nest</h3>")',
    )
    for fragment in required_navigation:
        if fragment not in navigation:
            raise SystemExit(f"Missing sidebar experiment wiring: {fragment}")
    dashboard_controls = (
        'self.refresh_button = style_button(',
        'QPushButton("Refresh")',
        'self.view_toggle_button = style_button(',
        'QPushButton("Grid View")',
        'controls.addWidget(self.refresh_button)',
        'controls.addWidget(self.view_toggle_button)',
        'controls.addWidget(self.sort_combo)',
    )
    missing_dashboard_controls = [
        item for item in dashboard_controls if item not in dashboard
    ]
    if missing_dashboard_controls:
        raise SystemExit(
            "Missing restored dashboard controls: "
            f"{missing_dashboard_controls}"
        )
    dashboard_order = (
        'controls.addWidget(self.refresh_button)',
        'controls.addWidget(self.view_toggle_button)',
        'controls.addWidget(self.sort_combo)',
    )
    dashboard_positions = [dashboard.index(item) for item in dashboard_order]
    if dashboard_positions != sorted(dashboard_positions):
        raise SystemExit(
            "Dashboard controls must be ordered Refresh, Grid/List View, Sort."
        )
    for removed_sidebar_control in (
        "self.dashboard_view_button",
        "self.refresh_button",
        "dashboard_view_toggle_requested",
    ):
        if removed_sidebar_control in navigation:
            raise SystemExit(
                "Dashboard Refresh/Grid controls must not remain in sidebar: "
                f"{removed_sidebar_control}"
            )

    for forbidden in (
        'item.setIcon(0, self._folder_icon)',
        'item.setIcon(0, self._script_icon)',
        '▦ Grid View',
        '☷ List View',
    ):
        if forbidden in navigation or forbidden in dashboard:
            raise SystemExit(
                f"Unexpected icon/symbol remains outside grid cards: {forbidden}"
            )

    # Original Python Lair 2 application-global menus must remain complete.
    global_menu_contract = (
        '"&New Script…"',
        '"New &Folder…"',
        '"&Import Script(s)…"',
        '"New &Workspace…"',
        '"Open W&orkspace…"',
        '"Open Script\'s Containing &Folder"',
        '"Open Current Folder E&xternally"',
        '"Open Current Folder in &Terminal"',
        '"Rename Current F&older…"',
        '"Remove Current Folder…"',
        '"&Save"',
        '"&Duplicate Current Script…"',
        '"E&xit"',
        '"&Preferences…"',
        '"Show &Dashboard"',
        '"&List View"',
        '"&Grid View"',
        '"Show &Sidebar"',
        '"&Full Screen"',
        '"&Documentation"',
        '"&Keyboard Shortcuts"',
        '"GitHub &Repository"',
        '"&Report an Issue"',
        '"&About Python Lair 2"',
    )
    missing_global = [item for item in global_menu_contract if item not in main_window]
    if missing_global:
        raise SystemExit(f"Original global menu contract incomplete: {missing_global}")

    # The screenshot/original View sequence must come first; new Sheepy-derived
    # options follow rather than displacing it.
    original_then_new_view = (
        '"Show &Dashboard"',
        '"&List View"',
        '"&Grid View"',
        '"Show &Sidebar"',
        '"&Full Screen"',
        '"View &Only"',
        '"&Word Wrap"',
        '"Line &Numbers"',
        '"Display &Font…"',
        '"Status &Bar"',
    )
    positions = [main_window.index(item) for item in original_then_new_view]
    if positions != sorted(positions):
        raise SystemExit(
            "Global View menu ordering does not preserve original Python Lair "
            "options before the newer Sheepy-derived items."
        )

    if "QMenuBar(" in editor_page or "editor_menu_bar" in editor_page:
        raise SystemExit(
            "Editor pages must not create a second QMenuBar; only the "
            "QMainWindow owns the application menu bar."
        )

    preferences_dialog = (
        package / "widgets/preferences_dialog.py"
    ).read_text(encoding="utf-8")
    preference_fragments = (
        'self.setWindowTitle("Preferences")',
        '"Choose the workspace Python Lair 2 should open on its next start."',
        '"Workspace folder:"',
        '"This will inform the location of your active workspace."',
        '"Show Setup Assistant on Next Start"',
    )
    missing_preferences = [
        item for item in preference_fragments if item not in preferences_dialog
    ]
    if missing_preferences:
        raise SystemExit(
            f"Preferences dialog contract incomplete: {missing_preferences}"
        )

    about_dialog = (
        package / "widgets/about_dialog.py"
    ).read_text(encoding="utf-8")
    about_fragments = (
        'self.setWindowTitle(f"About — {APP_BRAND_NAME}")',
        'self.setModal(False)',
        'self.setMinimumSize(700, 470)',
        'self.resize(700, 470)',
        'pixmap.scaled(',
        '112,',
        'APP_TAGLINE = "Friendly. Fast. Focused."',
        '"Built with Python and PyQt6.<br>"',
        'f"<b>Configuration:</b> {configuration_path}<br><br>"',
        'details.setWordWrap(True)',
        '"Licensed under the GNU General Public License v3 or later."',
    )
    missing_about = [item for item in about_fragments if item not in about_dialog]
    if missing_about:
        raise SystemExit(
            f"Pad-family About dialog contract incomplete: {missing_about}"
        )
    if "self.about_dialog: AboutDialog | None = None" not in main_window:
        raise SystemExit("About dialog must be retained/modeless and one-instance.")
    if "dialog.show()" not in main_window:
        raise SystemExit("About dialog must be shown modelessly.")

    if "set_dashboard_view_mode" in main_window:
        raise SystemExit(
            "MainWindow must not call removed sidebar set_dashboard_view_mode()."
        )

    direct_editor_order = (
        'self.launch_button = QPushButton("Launch")',
        'self.terminal_button = QPushButton("In Terminal")',
        'self.admin_button = QPushButton("As Admin")',
        'self.stop_button = QPushButton("Stop")',
        'self.force_stop_button = QPushButton("Force Stop")',
        'self.executable_button = QPushButton("Make Exec")',
        'self.cancel_changes_button = QPushButton("Cancel Changes")',
        'self.save_changes_button = QPushButton("Save Changes")',
    )
    direct_positions = [editor_page.index(item) for item in direct_editor_order]
    if direct_positions != sorted(direct_positions):
        raise SystemExit("Embedded editor direct-action button order is incorrect.")
    for state_fragment in (
        "button.setVisible(not running)",
        "button.setVisible(running)",
        "button.setEnabled(not running)",
        "button.setEnabled(running)",
        "lambda: self.stop_requested.emit(self.module)",
        "lambda: self.force_stop_requested.emit(self.module)",
    ):
        if state_fragment not in editor_page:
            raise SystemExit(
                f"Missing Sheepy-style Stop/Force Stop wiring: {state_fragment}"
            )

    navigation_geometry_fragments = (
        "SIDEBAR_MINIMUM_WIDTH = 205",
        "self.setMinimumWidth(SIDEBAR_MINIMUM_WIDTH)",
    )
    missing_navigation_geometry = [
        item for item in navigation_geometry_fragments
        if item not in navigation
    ]
    if missing_navigation_geometry:
        raise SystemExit(
            f"Sidebar geometry guard incomplete: {missing_navigation_geometry}"
        )

    splitter_geometry_fragments = (
        "self.splitter.setHandleWidth(8)",
        "self.splitter.setOpaqueResize(False)",
        "QTimer.singleShot(0, self._restore_splitter_geometry)",
        "def _restore_splitter_geometry(self)",
        "SIDEBAR_MINIMUM_WIDTH",
    )
    missing_splitter_geometry = [
        item for item in splitter_geometry_fragments
        if item not in main_window
    ]
    if missing_splitter_geometry:
        raise SystemExit(
            f"Splitter geometry guard incomplete: {missing_splitter_geometry}"
        )

    print("UI layout checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
