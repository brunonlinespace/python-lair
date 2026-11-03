# Python Lair 2
# SPDX-License-Identifier: GPL-3.0-or-later
"""Report the external-editor route chosen by Python Lair 2."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from PyQt6.QtCore import QCoreApplication

from python_lair2.services.runtime_launcher import (
    EDITOR_OVERRIDE_VARIABLE,
    RuntimeLauncher,
)
from python_lair2.services.runtime_paths import RuntimePaths


def main() -> int:
    app = QCoreApplication(sys.argv)
    project_root = Path(__file__).resolve().parents[2]
    runtime = RuntimePaths.detect(project_root / "main.py")
    launcher = RuntimeLauncher(runtime)

    print(f"Runtime: {runtime.runtime_label}")
    print(
        f"{EDITOR_OVERRIDE_VARIABLE}: "
        f"{os.environ.get(EDITOR_OVERRIDE_VARIABLE, '') or '(not set)'}"
    )
    print(f"xdg-open: {shutil.which('xdg-open') or '(not found)'}")
    print(f"gio: {shutil.which('gio') or '(not found)'}")
    print(f"EDITOR: {os.environ.get('EDITOR', '') or '(ignored)'}")
    print(f"VISUAL: {os.environ.get('VISUAL', '') or '(ignored)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
