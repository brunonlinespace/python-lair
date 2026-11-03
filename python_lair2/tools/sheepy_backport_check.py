#!/usr/bin/env python3
# Python Lair 2
# SPDX-License-Identifier: GPL-3.0-or-later
"""Static verification of Python-applicable Sheepy Pad backports."""

from pathlib import Path


def main() -> int:
    package = Path(__file__).resolve().parents[1]
    sources = {
        name: (package / relative).read_text(encoding="utf-8")
        for name, relative in {
            "window": "widgets/main_window.py",
            "page": "widgets/editor_page.py",
            "editor": "widgets/code_editor.py",
            "launcher": "services/runtime_launcher.py",
            "process": "services/process_manager.py",
            "runtime": "services/script_runtime.py",
            "config": "services/config_service.py",
            "navigation": "widgets/navigation.py",
            "file_io": "services/file_io.py",
        }.items()
    }

    required = {
        "window": (
            "View &Only", "&Word Wrap", "Line &Numbers", "Display &Font",
            "Run with &Arguments", "Syntax / &Lint Check",
            "Select &Interpreter", "Working &Directory",
            "Environment &Profiles", "Run as &Administrator",
            "Ctrl+Alt+X", "Run as Administrator?",
        ),
        "page": (
            'self.editor_file_menu = QMenu("File", self)',
            "Clear Search", "Find Previous", "Properties…",
            "MAX_FILE_BYTES", "MAX_SEARCH_MATCHES", "Exec: No", "UTF-8",
            "tokenize.detect_encoding", "file_disk_snapshot",
            "read_regular_file", "validated_symlink_target",
            "fsync_directory",
        ),
        "editor": (
            "MAX_PASTE_CHARACTERS", "MAX_DOCUMENT_CHARACTERS",
            "MAX_BRACKET_SCAN_CHARACTERS", "set_view_only",
            "overwrite_mode_changed", "set_word_wrap_enabled",
            "set_line_numbers_visible", "files_dropped",
        ),
        "launcher": (
            "resolve_interpreter", "detected_shebang", "elevated_script_command",
            "APPIMAGE_ORIGINAL_PATH", "process_start_time", "O_NOFOLLOW",
            "process.deleteLater()",
        ),
        "process": (
            "session_token = secrets.token_hex(32)",
            "def _read_terminal_state", "def _process_command_matches",
            "wrapper_start_time", "child_start_time", "terminal_start_time",
        ),
        "runtime": (
            "A profile may contain at most 16 variables.",
            "list(value.items())[:8]", "list(raw_values.items())[:16]",
        ),
        "config": (
            '"editor_word_wrap"', '"editor_line_numbers"',
            '"interpreter_override"', '"environment_profiles"',
            '"working_directory_mode"', "ensure_private_directory",
            "os.replace(temporary, self.path)",
        ),
        "file_io": (
            "def read_regular_file", "FileSnapshot", "FileStateChangedError",
            "def rename_path_no_replace", "def toggle_executable_permission",
            "def path_identity_matches",
        ),
    }
    missing = [
        f"{name}: {fragment}"
        for name, fragments in required.items()
        for fragment in fragments
        if fragment not in sources[name]
    ]
    if missing:
        raise SystemExit(f"Missing Sheepy backport wiring: {missing}")

    nav = sources["navigation"]
    if nav.index("self.dashboard_button = DashboardNavigationButton") >= nav.index(
        "self.workspace_label = QLabel"
    ):
        raise SystemExit("Dashboard/Workspace sidebar order is incorrect.")


    editor_source = sources["editor"]
    for fragment in (
        "EDITOR_COLOR_SCHEMES",
        "class SourceHighlighter(QSyntaxHighlighter)",
        '"keyword": "#c586c0"',
        '"string": "#ce9178"',
        '"comment": "#6a9955"',
        "_active_editor_color_scheme",
    ):
        if fragment not in editor_source:
            raise SystemExit(
                f"Missing Sheepy syntax-highlighting port: {fragment}"
            )
    print("Sheepy backport checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
