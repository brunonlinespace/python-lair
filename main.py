#!/usr/bin/env python3
"""Python Lair 2 launcher."""

from __future__ import annotations

import sys

from python_lair2 import APP_NAME, APP_VERSION


# Suite Pythoine may probe an extracted Portable tree before any build
# environment exists.  Keep this path dependency-free and exact.
if "--version" in sys.argv:
    print(f"{APP_NAME} {APP_VERSION}")
    raise SystemExit(0)

from python_lair2.app import main


if __name__ == "__main__":
    raise SystemExit(main())
