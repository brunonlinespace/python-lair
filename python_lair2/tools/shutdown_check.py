#!/usr/bin/env python3
# Python Lair 2
# SPDX-License-Identifier: GPL-3.0-or-later
"""Static verification of cancellable, responsive clean shutdown."""

from pathlib import Path


def main() -> int:
    package = Path(__file__).resolve().parents[1]
    scanner = (package / "services/module_scanner.py").read_text(encoding="utf-8")
    watcher = (package / "services/filesystem_watcher.py").read_text(encoding="utf-8")
    process = (package / "services/process_manager.py").read_text(encoding="utf-8")
    window = (package / "widgets/main_window.py").read_text(encoding="utf-8")

    required = (
        (scanner, "class ScanCancelled"),
        (scanner, "should_cancel"),
        (watcher, "thread.cancel()"),
        (watcher, "thread.wait(40)"),
        (watcher, "self._watcher.blockSignals(True)"),
        (process, "for module in tuple(self.repository.running)"),
        (process, "waitForFinished(40)"),
        (window, "ClosingDialog"),
        (window, "PYTHON_LAIR_PROFILE_SHUTDOWN"),
        (window, "self.watcher.stop("),
        (window, "self.process_manager.shutdown("),
        (window, "os._exit(0)"),
    )
    forbidden = (
        (watcher, "self._watcher.removePaths(watched)"),
        (process, "for _path, state in tuple(self.states)"),
    )

    missing = [fragment for source, fragment in required if fragment not in source]
    bad = [fragment for source, fragment in forbidden if fragment in source]
    if missing:
        raise SystemExit(f"Missing shutdown wiring: {missing}")
    if bad:
        raise SystemExit(f"Legacy shutdown wiring remains: {bad}")

    config_pos = window.index("self.config.update(")
    watcher_pos = window.index("self.watcher.stop(")
    process_pos = window.index("self.process_manager.shutdown(")
    exit_pos = window.index("os._exit(0)")
    if not (config_pos < watcher_pos < process_pos < exit_pos):
        raise SystemExit("Fast exit occurs before clean-shutdown prerequisites.")

    print("Clean shutdown checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
