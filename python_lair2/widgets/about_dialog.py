# Python Lair 2
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
"""About dialog for Python Lair 2."""

from __future__ import annotations

import html
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from python_lair2.app_constants import APP_BRAND_NAME, APP_VERSION, GITHUB_URL
from python_lair2.services.runtime_launcher import RuntimeLauncher


APP_TAGLINE = "Friendly. Fast. Focused."


class AboutDialog(QDialog):
    """Pad-family About dialog for Python Lair 2."""

    def __init__(
        self,
        icon_path: str | Path,
        config_path: str | Path,
        parent: QWidget | None = None,
        *,
        runtime_launcher: RuntimeLauncher | None = None,
    ) -> None:
        super().__init__(parent)
        self.runtime_launcher = runtime_launcher
        self.setWindowTitle(f"About — {APP_BRAND_NAME}")
        self.setModal(False)
        self.setMinimumSize(700, 470)
        self.resize(700, 470)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(10)

        pixmap = QPixmap(str(icon_path))
        if not pixmap.isNull():
            logo = QLabel(self)
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo.setPixmap(
                pixmap.scaled(
                    112,
                    112,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            layout.addWidget(logo)

        application_name = QLabel(f"<h2>{APP_BRAND_NAME}</h2>", self)
        application_name.setTextFormat(Qt.TextFormat.RichText)
        application_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(application_name)

        version = QLabel(f"Version {APP_VERSION}", self)
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        tagline = QLabel(f"<b>{APP_TAGLINE}</b>", self)
        tagline.setTextFormat(Qt.TextFormat.RichText)
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tagline)

        description = QLabel(
            "A lightweight Python IDE and launcher for Linux, combining "
            "workspace management, focused source editing and practical "
            "launch tools.",
            self,
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)

        configuration_path = html.escape(str(config_path)).replace("/", "/&#8203;")
        details = QLabel(
            f"<a href='{GITHUB_URL}'>{GITHUB_URL}</a><br>"
            "Built with Python and PyQt6.<br>"
            f"<b>Configuration:</b> {configuration_path}<br><br>"
            "Copyright © 2026 Bruno Machado<br>"
            "[<a href='https://github.com/brunonlinespace/'>"
            "https://github.com/brunonlinespace/</a>]<br>"
            "Licensed under the GNU General Public License v3 or later.",
            self,
        )
        details.setTextFormat(Qt.TextFormat.RichText)
        details.setWordWrap(True)
        details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        details.setOpenExternalLinks(False)
        details.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        details.linkActivated.connect(self._open_link)
        layout.addWidget(details)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, self)
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setText("OK")
        buttons.accepted.connect(self.close)
        layout.addWidget(buttons)

    def _open_link(self, url: str) -> None:
        if self.runtime_launcher is not None:
            self.runtime_launcher.open_url(url)
