# Python Lair 2
# SPDX-License-Identifier: GPL-3.0-or-later
"""Quick repository sort-order diagnostic."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QCoreApplication

from python_lair2.models.module import Module
from python_lair2.models.module_repository import ModuleRepository


def module(name: str, created: float, modified: float) -> Module:
    path = Path("/tmp") / f"{name}.py"
    return Module(
        path=path,
        filename=path.name,
        display_name=name,
        folder="",
        created=created,
        modified=modified,
        size=1,
        executable=False,
    )


def main() -> int:
    app = QCoreApplication([])
    repository = ModuleRepository()
    repository.add_many(
        (
            module("Charlie", 2, 1),
            module("Alpha", 1, 3),
            module("Bravo", 3, 2),
        )
    )

    expected = {
        "title_az": ["Alpha", "Bravo", "Charlie"],
        "title_za": ["Charlie", "Bravo", "Alpha"],
        "created": ["Bravo", "Charlie", "Alpha"],
        "modified": ["Alpha", "Bravo", "Charlie"],
    }

    for mode, names in expected.items():
        actual = [item.display_name for item in repository.sorted(mode=mode)]
        if actual != names:
            raise SystemExit(f"{mode}: expected {names}, got {actual}")

    print("Repository sorting: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
