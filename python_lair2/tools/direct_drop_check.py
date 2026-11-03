# Python Lair 2
# SPDX-License-Identifier: GPL-3.0-or-later
"""Static verification of direct external folder-drop routes."""

from pathlib import Path


def main() -> int:
    package = Path(__file__).resolve().parents[1]
    navigation = (package / "widgets/navigation.py").read_text(encoding="utf-8")
    folder = (package / "widgets/folder_dashboard.py").read_text(encoding="utf-8")
    manager = (package / "controllers/editor_manager.py").read_text(encoding="utf-8")
    actions = (package / "controllers/file_actions.py").read_text(encoding="utf-8")
    window = (package / "widgets/main_window.py").read_text(encoding="utf-8")

    required = (
        (navigation, "external_python_paths"),
        (navigation, "external_files_import_requested"),
        (folder, "external_files_dropped"),
        (folder, "def dropEvent"),
        (manager, "external_files_import_requested"),
        (actions, "destination_folder"),
        (actions, "destination.parent"),
        (window, "navigation.external_files_import_requested.connect"),
        (window, "editor_manager.external_files_import_requested.connect"),
    )
    missing = [fragment for source, fragment in required if fragment not in source]
    if missing:
        raise SystemExit(f"Missing direct-drop wiring: {missing}")

    print("Direct folder-drop wiring: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
