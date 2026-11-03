# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Runtime and filesystem paths for source, frozen, and AppImage builds."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from PyQt6.QtCore import QStandardPaths


WORKSPACE_ENVIRONMENT_VARIABLE = "PYTHON_LAIR_WORKSPACE"
APPIMAGE_ENVIRONMENT_VARIABLE = "APPIMAGE"
APPDIR_ENVIRONMENT_VARIABLE = "APPDIR"


@dataclass(frozen=True, slots=True)
class RuntimePaths:
    """Resolved locations used by the current Python Lair 2 process."""

    launcher_root: Path
    package_root: Path
    resource_root: Path
    config_root: Path
    default_workspace: Path
    running_as_appimage: bool
    running_frozen: bool

    @classmethod
    def detect(cls, launcher_file: str | Path) -> "RuntimePaths":
        """Resolve paths without relying on the shell's working directory."""
        launcher_root = Path(launcher_file).resolve().parent
        running_as_appimage = bool(os.environ.get(APPIMAGE_ENVIRONMENT_VARIABLE))
        running_frozen = bool(getattr(sys, "frozen", False))

        # PyInstaller may expose bundled resources through _MEIPASS. In an
        # onedir bundle this normally points at the bundle root; in source
        # mode the package remains beside main.py.
        frozen_root_value = getattr(sys, "_MEIPASS", None)
        frozen_root = (
            Path(frozen_root_value).resolve()
            if frozen_root_value
            else launcher_root
        )

        source_package_root = launcher_root / "python_lair2"
        bundled_package_root = frozen_root / "python_lair2"
        package_root = (
            bundled_package_root
            if bundled_package_root.exists()
            else source_package_root
        )

        config_location = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppConfigLocation
        )
        config_root = (
            Path(config_location).expanduser().resolve(strict=False)
            if config_location
            else Path.home() / ".config" / "python-lair-2"
        )

        default_workspace = cls._resolve_default_workspace(
            launcher_root=launcher_root,
            running_as_appimage=running_as_appimage,
            running_frozen=running_frozen,
        )

        return cls(
            launcher_root=launcher_root,
            package_root=package_root,
            resource_root=package_root / "assets",
            config_root=config_root,
            default_workspace=default_workspace,
            running_as_appimage=running_as_appimage,
            running_frozen=running_frozen,
        )

    @staticmethod
    def _resolve_default_workspace(
        *,
        launcher_root: Path,
        running_as_appimage: bool,
        running_frozen: bool,
    ) -> Path:
        """Choose a writable default while preserving portable source mode."""
        environment_override = os.environ.get(
            WORKSPACE_ENVIRONMENT_VARIABLE,
            "",
        ).strip()
        if environment_override:
            return Path(environment_override).expanduser().resolve(strict=False)

        # A source checkout or extracted portable folder deliberately keeps
        # its workspace beside main.py. Frozen/AppImage bundles must never use
        # their installation or mount directory as writable user storage.
        if not running_as_appimage and not running_frozen:
            return launcher_root / "my library"

        documents_location = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        documents_root = (
            Path(documents_location).expanduser().resolve(strict=False)
            if documents_location
            else Path.home() / "Documents"
        )
        return documents_root / "Python Lair Workspace"

    def resolve_workspace(self, configured_workspace: object) -> Path:
        """Return the configured workspace or the runtime-appropriate default."""
        if isinstance(configured_workspace, str) and configured_workspace.strip():
            return Path(configured_workspace).expanduser().resolve(strict=False)
        return self.default_workspace.resolve(strict=False)

    def ensure_writable_workspace(self, workspace: str | Path) -> Path:
        """Create the workspace and verify that files can be written there."""
        path = Path(workspace).expanduser().resolve(strict=False)
        path.mkdir(parents=True, exist_ok=True)

        probe_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path,
                prefix=".python-lair-write-test-",
                delete=False,
            ) as probe:
                probe.write("ok")
                probe_path = Path(probe.name)
        finally:
            if probe_path is not None:
                try:
                    probe_path.unlink()
                except OSError:
                    pass
        return path

    @property
    def icon_path(self) -> Path:
        return self.resource_root / "icons" / "python-lair-2.png"

    @property
    def config_path(self) -> Path:
        return self.config_root / "python_lair_2_config.json"

    @property
    def runtime_label(self) -> str:
        if self.running_as_appimage:
            return "AppImage"
        if self.running_frozen:
            return "Frozen bundle"
        return "Portable source"
