# Python Lair 2
# SPDX-License-Identifier: GPL-3.0-or-later
"""Print runtime launcher decisions without starting the GUI."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import QCoreApplication

from python_lair2.services.runtime_launcher import RuntimeLauncher
from python_lair2.services.runtime_paths import RuntimePaths


def main() -> int:
    app = QCoreApplication(sys.argv)
    runtime = RuntimePaths.detect(Path(__file__).resolve().parents[2] / "main.py")
    launcher = RuntimeLauncher(runtime)

    print(f"Runtime: {runtime.runtime_label}")
    print(f"sys.executable: {sys.executable}")
    print(f"Host Python: {launcher.python_executable()}")
    print(f"PATH: {os.environ.get('PATH', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
