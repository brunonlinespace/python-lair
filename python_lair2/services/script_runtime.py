# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Argument and environment-profile helpers adapted from Sheepy Pad."""

from __future__ import annotations

import os
import re
import shlex

_ENVIRONMENT_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def parse_argument_string(value: str) -> tuple[str, ...]:
    """Split one user-entered argument string without invoking a shell."""
    if not value.strip():
        return ()
    return tuple(shlex.split(value, posix=os.name != "nt"))


def parse_environment_lines(text: str) -> dict[str, str]:
    """Parse one NAME=value environment entry per line."""
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Line {line_number} must use NAME=value format.")
        key, value = line.split("=", 1)
        key = key.strip()
        if not _ENVIRONMENT_NAME.fullmatch(key):
            raise ValueError(
                f"Line {line_number} has an invalid variable name: {key!r}."
            )
        if len(value) > 1536:
            raise ValueError(
                f"Line {line_number} has a value longer than 1536 characters."
            )
        values[key] = value
        if len(values) > 16:
            raise ValueError("A profile may contain at most 16 variables.")
    return values


def format_environment_lines(values: dict[str, str]) -> str:
    """Format environment variables in stable case-insensitive order."""
    return "\n".join(f"{name}={values[name]}" for name in sorted(values))


def normalise_environment_profiles(value: object) -> dict[str, dict[str, str]]:
    """Validate environment-profile JSON while preserving a Default profile."""
    profiles: dict[str, dict[str, str]] = {"Default": {}}
    if not isinstance(value, dict):
        return profiles

    for raw_name, raw_values in list(value.items())[:8]:
        if not isinstance(raw_name, str):
            continue
        name = raw_name.strip()
        if not name or len(name) > 64 or not isinstance(raw_values, dict):
            continue
        clean: dict[str, str] = {}
        for raw_key, raw_value in list(raw_values.items())[:16]:
            if (
                isinstance(raw_key, str)
                and _ENVIRONMENT_NAME.fullmatch(raw_key)
                and isinstance(raw_value, str)
                and len(raw_value) <= 1536
            ):
                clean[raw_key] = raw_value
        profiles[name] = clean

    profiles.setdefault("Default", {})
    return profiles
