# Python Lair 2
# SPDX-License-Identifier: GPL-3.0-or-later
"""Static check that important UI actions are connected to runtime services."""

from __future__ import annotations

from pathlib import Path


def require(text: str, fragment: str, file_name: str) -> None:
    if fragment not in text:
        raise SystemExit(f"Missing route in {file_name}: {fragment}")


def main() -> int:
    package = Path(__file__).resolve().parents[1]

    editor = (package / "widgets" / "editor_page.py").read_text(encoding="utf-8")
    manager = (package / "controllers" / "editor_manager.py").read_text(
        encoding="utf-8"
    )
    actions = (package / "controllers" / "file_actions.py").read_text(
        encoding="utf-8"
    )
    window = (package / "widgets" / "main_window.py").read_text(encoding="utf-8")
    process = (package / "services" / "process_manager.py").read_text(
        encoding="utf-8"
    )

    checks = (
        (editor, "containing_folder_requested", "editor_page.py"),
        (editor, "Open Containing Folder", "editor_page.py"),
        (manager, "containing_folder_requested", "editor_manager.py"),
        (actions, "def open_module_folder", "file_actions.py"),
        (actions, "runtime_launcher.open_path(folder)", "file_actions.py"),
        (
            window,
            "editor_manager.containing_folder_requested.connect",
            "main_window.py",
        ),
        (window, "open_script_folder_action", "main_window.py"),
        (process, "runtime_launcher.script_command", "process_manager.py"),
        (process, "runtime_launcher.script_terminal_command", "process_manager.py"),
    )

    for text, fragment, file_name in checks:
        require(text, fragment, file_name)

    print("Acceptance routes: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
