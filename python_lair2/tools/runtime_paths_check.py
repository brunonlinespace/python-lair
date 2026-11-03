#!/usr/bin/env python3
# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Print runtime path decisions for packaging diagnostics."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from python_lair2.services.runtime_paths import RuntimePaths


def main() -> int:
    app = QApplication.instance() or QApplication([])
    project_main = Path(__file__).resolve().parents[2] / "main.py"
    runtime = RuntimePaths.detect(project_main)
    for key, value in asdict(runtime).items():
        print(f"{key}: {value}")
    print(f"icon_path: {runtime.icon_path}")
    print(f"config_path: {runtime.config_path}")
    print(f"runtime_label: {runtime.runtime_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
