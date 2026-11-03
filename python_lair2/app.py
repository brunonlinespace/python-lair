#!/usr/bin/env python3
# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
"""Python Lair 2 application entry point."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from python_lair2 import APP_NAME as SUITE_APP_NAME, APP_VERSION
from python_lair2.app_constants import (
    APP_DISPLAY_NAME,
    APP_INTERNAL_NAME,
    ORGANIZATION_DOMAIN,
    ORGANIZATION_NAME,
)
from python_lair2.services.config_service import ConfigService
from python_lair2.services.runtime_paths import RuntimePaths
from python_lair2.widgets.first_run_dialog import FirstRunWizard
from python_lair2.widgets.main_window import MainWindow



def main() -> int:
    if "--version" in sys.argv:
        print(f"{SUITE_APP_NAME} {APP_VERSION}")
        return 0

    app = QApplication(sys.argv)
    # Keep the internal identifier separate from the visible caption.
    app.setApplicationName(APP_INTERNAL_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setOrganizationDomain(ORGANIZATION_DOMAIN)
    app.setDesktopFileName(APP_INTERNAL_NAME)

    runtime = RuntimePaths.detect(Path(__file__).resolve().parents[1] / "main.py")
    if runtime.icon_path.exists():
        app.setWindowIcon(QIcon(str(runtime.icon_path)))

    config_path = runtime.config_path
    config_existed_before_startup = config_path.exists()
    migration_candidates = (
        runtime.launcher_root / "python_lair_2_config.json",
        runtime.launcher_root / "suite_config.json",
    )
    if not config_path.exists():
        for legacy_config_path in migration_candidates:
            if not legacy_config_path.exists():
                continue
            try:
                config_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(legacy_config_path, config_path)
                break
            except OSError:
                continue
    config = ConfigService(config_path)

    force_setup = "--setup" in sys.argv
    should_show_setup = force_setup or (
        not bool(config.get("setup_completed", False))
        and (
            not config_existed_before_startup
            or bool(config.get("show_setup_assistant", False))
        )
    )

    if should_show_setup:
        assistant = FirstRunWizard(runtime)
        if assistant.exec():
            configured_workspace = str(assistant.selected_workspace)
        else:
            # Cancel remains safe and non-blocking: use the runtime default
            # and do not show the assistant again automatically.
            configured_workspace = str(runtime.default_workspace)

        config.update(
            {
                "workspace_path": configured_workspace,
                "setup_completed": True,
                "show_setup_assistant": False,
            },
            save=True,
        )
    else:
        configured_workspace = config.get("workspace_path")

    requested_workspace = runtime.resolve_workspace(configured_workspace)

    try:
        library_root = runtime.ensure_writable_workspace(requested_workspace)
    except OSError as error:
        # Do not silently attempt to write inside a read-only AppImage mount.
        # Falling back to the runtime default also repairs stale configurations
        # that point to an unavailable removable drive or deleted directory.
        fallback = runtime.ensure_writable_workspace(runtime.default_workspace)
        library_root = fallback
        config.set("workspace_path", str(fallback), save=True)
        print(
            f"Workspace '{requested_workspace}' was unavailable ({error}); "
            f"using '{fallback}'.",
            file=sys.stderr,
        )

    window = MainWindow(
        library_root,
        config,
        runtime,
        icon_path=runtime.icon_path,
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
