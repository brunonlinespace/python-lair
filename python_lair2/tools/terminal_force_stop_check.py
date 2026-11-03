# Python Lair 2
# SPDX-License-Identifier: GPL-3.0-or-later
"""Static verification of dedicated terminal Force Stop wiring."""

from pathlib import Path


def main() -> int:
    package = Path(__file__).resolve().parents[1]
    launcher = (package / "services/runtime_launcher.py").read_text(
        encoding="utf-8"
    )
    manager = (package / "services/process_manager.py").read_text(
        encoding="utf-8"
    )

    required = (
        (launcher, "def start_detached_with_pid"),
        (launcher, '("konsole", ("--nofork", "-e", *command_parts))'),
        (manager, '"terminal_pid": terminal_pid'),
        (manager, '"terminal_start_time": ('),
        (manager, "def _read_terminal_state"),
        (manager, "def _process_command_matches"),
        (manager, "expected_values=expected_terminal"),
        (manager, "os.killpg(child_pgid, sig)"),
    )
    missing = [fragment for source, fragment in required if fragment not in source]
    if missing:
        raise SystemExit(f"Missing terminal Force Stop wiring: {missing}")

    print("Terminal Force Stop wiring: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
