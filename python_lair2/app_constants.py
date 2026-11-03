# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared application identity and metadata."""

from python_lair2 import (
    APP_ID,
    APP_NAME as SUITE_APP_NAME,
    APP_VERSION,
    DESKTOP_ID,
    PUBLISHER_ID,
)

# Visible product branding remains Python Lair 2.  The canonical Suite/package
# identity is Python Lair / python-lair and lives in python_lair2.__init__.
APP_INTERNAL_NAME = "python-lair-2"
APP_BRAND_NAME = "Python Lair 2"
APP_DISPLAY_NAME = "Python Lair 2 — Lightweight Python IDE"
APP_WINDOW_TITLE = APP_DISPLAY_NAME

ORGANIZATION_NAME = "brunonlinespace"
ORGANIZATION_DOMAIN = "github.com/brunonlinespace"

GITHUB_URL = "https://github.com/brunonlinespace/python-lair"
ISSUES_URL = f"{GITHUB_URL}/issues"
