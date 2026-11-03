#!/usr/bin/env python3
# Python Lair 2
# SPDX-License-Identifier: GPL-3.0-or-later
"""Static release checks that do not require PyQt6 or a display server."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PACKAGE_ROOT.parent
ROOT = SOURCE_ROOT
EXPECTED_VERSION = "2.1.1"
ROOT_README_NORMALIZED_SHA256 = "1da51936525373da0cde8b9311556dce6529042e61ea08869b7eacfd3ee59b5d"

# Generated build environments must never be treated as release source.
# Python caches in the working tree are ordinary local artifacts and are
# ignored by Git. They only become a release error when Git reports that they
# are actually tracked.
GENERATED_ROOT_NAMES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "ENV",
    "build",
    "dist",
    "dist-appimage",
    "AppDir",
    "PythonLair2.AppDir",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "my library",
}


def relative_parts(path: Path) -> tuple[str, ...]:
    try:
        return path.relative_to(ROOT).parts
    except ValueError:
        return path.parts


def is_generated_area(path: Path) -> bool:
    return any(part in GENERATED_ROOT_NAMES for part in relative_parts(path))


def is_python_cache_path(path: Path) -> bool:
    parts = relative_parts(path)
    return "__pycache__" in parts or path.suffix in {".pyc", ".pyo"}


def tracked_python_cache_files() -> list[Path]:
    """Return cache files tracked by Git, or an empty list outside a checkout."""
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z"],
            check=False,
            capture_output=True,
        )
    except OSError:
        return []

    if result.returncode != 0:
        return []

    tracked: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        try:
            relative = Path(raw.decode("utf-8"))
        except UnicodeDecodeError:
            continue
        candidate = ROOT / relative
        if is_python_cache_path(candidate):
            tracked.append(relative)
    return sorted(tracked)


def local_python_cache_paths() -> list[Path]:
    """Return non-build cache paths for a helpful, non-failing notice."""
    return sorted(
        path.relative_to(ROOT)
        for path in ROOT.rglob("*")
        if not is_generated_area(path) and is_python_cache_path(path)
    )


def read_png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
        raise ValueError("not a valid PNG")
    return struct.unpack(">II", data[16:24])



def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_identity() -> dict[str, str]:
    """Read the dependency-free canonical identity from python_lair2/__init__.py."""
    source = (PACKAGE_ROOT / "__init__.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    wanted = {
        "APP_NAME",
        "APP_ID",
        "APP_VERSION",
        "PUBLISHER_ID",
        "DESKTOP_ID",
    }
    values: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in wanted:
                values[target.id] = node.value.value
    return values


def main() -> int:
    errors: list[str] = []

    root_entries = {
        path.name
        for path in SOURCE_ROOT.iterdir()
        if path.name != "__pycache__"
    }
    if root_entries != {"README.md", "main.py", "suite-pythoine-component.json", "python_lair2"}:
        errors.append(
            "Source root must contain only README.md, main.py, suite-pythoine-component.json and python_lair2/: "
            f"{sorted(root_entries)}"
        )

    root_readme = SOURCE_ROOT / "README.md"
    if not root_readme.is_file():
        errors.append("Missing locked public root README.md")
    else:
        readme_text = root_readme.read_text(encoding="utf-8")
        if f"Current release: **{EXPECTED_VERSION}**" not in readme_text:
            errors.append("Root README.md current-release version is stale")
        normalized_readme = readme_text.replace(EXPECTED_VERSION, "@VERSION@")
        normalized_hash = hashlib.sha256(normalized_readme.encode("utf-8")).hexdigest()
        if normalized_hash != ROOT_README_NORMALIZED_SHA256:
            errors.append(
                "Locked root README.md content changed outside permitted version-number updates"
            )

    for source in sorted(ROOT.rglob("*.py")):
        if is_generated_area(source) or "__pycache__" in relative_parts(source):
            continue
        try:
            ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except (OSError, SyntaxError, UnicodeError) as exc:
            errors.append(f"{source.relative_to(ROOT)}: {exc}")

    required = (
        ".gitignore",
        ".gitattributes",
        "LICENSE",
        "docs/README.md",
        "docs/CHANGELOG.md",
        "docs/CONTRIBUTING.md",
        "docs/SECURITY.md",
        "docs/BUILDING.md",
        "docs/QA.md",
        "docs/ARCHITECTURE.md",
        "docs/PROJECT_MEMORY.md",
        "docs/ROADMAP.md",
        "docs/RELEASE_NOTES.md",
        "docs/RELEASE_CHECKLIST.md",
        "requirements.txt",
        ".python-lair-ignore.example",
        "python-lair.json",
        "SOURCE_MANIFEST.sha256",
        "packaging/appimage/python-lair-2.desktop",
        "packaging/appimage/io.github.brunonlinespace.python_lair.metainfo.xml",
        "packaging/fedora/build-appimage.sh",
        "packaging/fedora/install-build-deps.sh",
        "packaging/pyinstaller/build-requirements.txt",
        "packaging/fedora/test-appimage.sh",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
        ".github/pull_request_template.md",
    )
    for relative in required:
        if not (PACKAGE_ROOT / relative).is_file():
            errors.append(f"Missing required program file: {relative}")

    launcher = (SOURCE_ROOT / "main.py").read_text(encoding="utf-8")
    if "from python_lair2.app import main" not in launcher:
        errors.append(
            "Root main.py must be a location-independent python_lair2.app launcher"
        )

    expected_package_identity = {
        "APP_NAME": "Python Lair",
        "APP_ID": "python-lair",
        "APP_VERSION": EXPECTED_VERSION,
        "PUBLISHER_ID": "brunonlinespace",
        "DESKTOP_ID": "io.github.brunonlinespace.python_lair",
    }
    actual_package_identity = package_identity()
    for key, expected in expected_package_identity.items():
        if actual_package_identity.get(key) != expected:
            errors.append(
                f"Package identity mismatch: {key} "
                f"(expected {expected!r}, got {actual_package_identity.get(key)!r})"
            )

    project_manifest = PACKAGE_ROOT / "python-lair.json"
    expected_identity = {
        "name": "Python Lair",
        "id": "python-lair",
        "version": EXPECTED_VERSION,
        "publisher_id": "brunonlinespace",
        "desktop_id": "io.github.brunonlinespace.python_lair",
        "repository": "https://github.com/brunonlinespace/python-lair",
        "tagline": "Friendly. Fast. Focused.",
    }
    try:
        manifest_identity = json.loads(project_manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"Invalid Python Lair project manifest: {exc}")
        manifest_identity = {}
    for key, expected in expected_identity.items():
        if manifest_identity.get(key) != expected:
            errors.append(
                f"Project manifest identity mismatch: {key} "
                f"(expected {expected!r}, got {manifest_identity.get(key)!r})"
            )

    package_to_manifest = {
        "APP_NAME": "name",
        "APP_ID": "id",
        "APP_VERSION": "version",
        "PUBLISHER_ID": "publisher_id",
        "DESKTOP_ID": "desktop_id",
    }
    for package_key, manifest_key in package_to_manifest.items():
        if actual_package_identity.get(package_key) != manifest_identity.get(manifest_key):
            errors.append(
                "Package/manifest identity disagreement: "
                f"{package_key} != {manifest_key}"
            )

    component_manifest = SOURCE_ROOT / "suite-pythoine-component.json"
    expected_component = {
        "id": "python-lair",
        "name": "Python Lair",
        "version": EXPECTED_VERSION,
        "component_kind": "extension",
        "extensions": [],
        "portable_command": ["main.py"],
        "icon": "python_lair2/assets/icons/python-lair-2.png",
        "publisher": "brunonlinespace",
        "publisher_id": "brunonlinespace",
        "repository": "https://github.com/brunonlinespace/python-lair",
        "desktop_id": "python-lair",
        "tagline": "Friendly. Fast. Focused.",
        "capabilities": {"routing": False, "open": False, "create": False},
    }
    try:
        component_identity = json.loads(component_manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"Invalid Suite Pythoine component manifest: {exc}")
        component_identity = {}
    for key, expected in expected_component.items():
        if component_identity.get(key) != expected:
            errors.append(
                f"Suite component manifest mismatch: {key} "
                f"(expected {expected!r}, got {component_identity.get(key)!r})"
            )

    # This is the same simple source identity surface Suite can safely probe:
    # it must work without PyQt6 and must print exactly '<name> <version>'.
    expected_probe = f"{expected_identity['name']} {EXPECTED_VERSION}"
    try:
        probe = subprocess.run(
            [sys.executable, str(SOURCE_ROOT / "main.py"), "--version"],
            cwd=SOURCE_ROOT,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        errors.append(f"Portable identity probe could not run: {exc}")
    else:
        if probe.returncode != 0:
            errors.append(
                "Portable identity probe failed: "
                f"exit={probe.returncode}, stderr={probe.stderr.strip()!r}"
            )
        elif probe.stdout.strip() != expected_probe:
            errors.append(
                "Portable identity probe mismatch: "
                f"expected {expected_probe!r}, got {probe.stdout.strip()!r}"
            )

    metadata_checks = {
        "packaging/appimage/python-lair-2.desktop": f"X-AppImage-Version={EXPECTED_VERSION}",
        "packaging/appimage/io.github.brunonlinespace.python_lair.metainfo.xml": f'<release version="{EXPECTED_VERSION}"',
        "packaging/fedora/build-appimage.sh": f'APP_VERSION="{EXPECTED_VERSION}"',
        "docs/RELEASE_CHECKLIST.md": f"Python Lair {EXPECTED_VERSION}",
    }
    for relative, fragment in metadata_checks.items():
        path = PACKAGE_ROOT / relative
        if path.is_file() and fragment not in path.read_text(encoding="utf-8"):
            errors.append(f"Version metadata mismatch in {relative}: {fragment}")

    build_script = PACKAGE_ROOT / "packaging/fedora/build-appimage.sh"
    if build_script.is_file():
        build_text = build_script.read_text(encoding="utf-8")
        release_check_call = build_text.find("$PROGRAM_ROOT/tools/release_check.py")
        venv_creation = build_text.find('python3 -m venv "$VENV"')
        if release_check_call < 0 or venv_creation < 0:
            errors.append("Fedora build script is missing validation or venv creation")
        elif release_check_call > venv_creation:
            errors.append("Fedora build script creates the venv before source validation")

        for fragment in (
            'APP_NAME="Python Lair"',
            'APP_ID="python-lair"',
            'APP_VERSION="2.1.1"',
            'PROJECT_MANIFEST="$PROGRAM_ROOT/python-lair.json"',
            'SOURCE_MANIFEST="$PROGRAM_ROOT/SOURCE_MANIFEST.sha256"',
            'COMPONENT_MANIFEST="$PROJECT_ROOT/suite-pythoine-component.json"',
            'ROOT_README="$PROJECT_ROOT/README.md"',
            'Root README.md SHA-256:',
            'BUILD_REQUIREMENTS="$PROGRAM_ROOT/packaging/pyinstaller/build-requirements.txt"',
            'validate_build_root',
            'python3 -m venv "$VENV"',
            'pip check',
            'pip freeze --all',
            'APPIMAGETOOL_SHA256',
            'run_version_smoke_test "final AppImage"',
            '"$PROJECT_MANIFEST"',
            '"$SOURCE_MANIFEST"',
            "Suite component manifest SHA-256:",
            "Project manifest SHA-256:",
            "SOURCE_MANIFEST.sha256 SHA-256:",
        ):
            if fragment not in build_text:
                errors.append(
                    "Fedora builder is missing Suite/provenance integration: "
                    f"{fragment}"
                )

    build_requirements = PACKAGE_ROOT / "packaging/pyinstaller/build-requirements.txt"
    if build_requirements.is_file():
        build_requirement_text = build_requirements.read_text(encoding="utf-8")
        for pinned in (
            "PyInstaller==6.21.0",
            "pyinstaller-hooks-contrib==2026.6",
        ):
            if pinned not in build_requirement_text:
                errors.append(f"Missing pinned build requirement: {pinned}")

    about_text = (PACKAGE_ROOT / "widgets/about_dialog.py").read_text(encoding="utf-8")
    for fragment in (
        'APP_TAGLINE = "Friendly. Fast. Focused."',
        'self.setMinimumSize(700, 470)',
        'self.resize(700, 470)',
        'f"<b>Configuration:</b> {configuration_path}<br><br>"',
        'details.setWordWrap(True)',
    ):
        if fragment not in about_text:
            errors.append(f"Plus-family About contract missing: {fragment}")

    try:
        import xml.etree.ElementTree as ET
        appstream_root = ET.parse(PACKAGE_ROOT / "packaging/appimage/io.github.brunonlinespace.python_lair.metainfo.xml").getroot()
        developer = appstream_root.find("developer[@id='io.github.brunonlinespace']")
        if developer is None or (developer.findtext("name") or "").strip() != "Bruno Machado":
            errors.append("AppStream structured developer metadata is missing or incorrect")
        if appstream_root.find("content_rating[@type='oars-1.1']") is None:
            errors.append("AppStream OARS 1.1 content rating is missing")
        releases = appstream_root.findall("./releases/release")
        if len(releases) != 1 or releases[0].attrib.get("version") != EXPECTED_VERSION:
            errors.append("AppStream release feed must contain only the current release")
    except (OSError, ET.ParseError) as exc:
        errors.append(f"Invalid AppStream metadata: {exc}")

    icon_expectations = {
        "python-lair-2-16.png": (16, 16),
        "python-lair-2-32.png": (32, 32),
        "python-lair-2-48.png": (48, 48),
        "python-lair-2-64.png": (64, 64),
        "python-lair-2-128.png": (128, 128),
        "python-lair-2-256.png": (256, 256),
        "python-lair-2.png": (512, 512),
        "dashboard-16.png": (16, 16),
        "dashboard-20.png": (20, 20),
        "dashboard-24.png": (24, 24),
        "dashboard-32.png": (32, 32),
        "dashboard-48.png": (48, 48),
        "dashboard-64.png": (64, 64),
        "dashboard.png": (24, 24),
        "folder-16.png": (16, 16),
        "folder-24.png": (24, 24),
        "folder-32.png": (32, 32),
        "folder-48.png": (48, 48),
        "folder-64.png": (64, 64),
        "folder.png": (32, 32),
        "script-16.png": (16, 16),
        "script-24.png": (24, 24),
        "script-32.png": (32, 32),
        "script-48.png": (48, 48),
        "script-64.png": (64, 64),
        "script.png": (32, 32),
    }
    icon_root = PACKAGE_ROOT / "assets/icons"
    for filename, expected_size in icon_expectations.items():
        path = icon_root / filename
        if not path.is_file():
            errors.append(f"Missing icon: {path.relative_to(ROOT)}")
            continue
        try:
            actual_size = read_png_size(path)
        except (OSError, ValueError) as exc:
            errors.append(f"Invalid icon {path.relative_to(ROOT)}: {exc}")
            continue
        if actual_size != expected_size:
            errors.append(
                f"Wrong icon size {path.relative_to(ROOT)}: "
                f"{actual_size}, expected {expected_size}"
            )

    source_safety_checks = {
        "controllers/file_actions.py": (
            "destination.parent,",
            "def _unique_destination(folder: Path",
            "if clicked not in (keep_both, replace):",
        ),
        "widgets/dashboard_card.py": (
            "display_name = escape(self.module.display_name)",
            "filename = escape(self.module.filename)",
        ),
        "widgets/editor_page.py": (
            "return False",
            "replace_document_text(result)",
            "display_name = escape(self.module.display_name)",
            "path_text = escape(str(self.module.path))",
        ),
        "services/module_scanner.py": (
            "executable=bool(info.st_mode & 0o111)",
        ),
        "services/runtime_paths.py": (
            "with NamedTemporaryFile(",
            'prefix=".python-lair-write-test-"',
        ),
        "services/config_service.py": (
            "ensure_private_directory(self.path.parent)",
            "tempfile.mkstemp(",
            "os.fsync(handle.fileno())",
            "os.replace(temporary, self.path)",
            "fsync_directory(self.path.parent)",
        ),
        "services/file_io.py": (
            "def read_regular_file(",
            "def current_file_state(",
            "def path_identity_matches(",
            "def toggle_executable_permission(",
            "def rename_path_no_replace(",
        ),
        "widgets/main_window.py": (
            'SHUTDOWN_PROFILE_ENV = "PYTHON_LAIR_PROFILE_SHUTDOWN"',
        ),
    }
    for relative, fragments in source_safety_checks.items():
        path = PACKAGE_ROOT / relative
        if not path.is_file():
            errors.append(f"Missing safety-critical source: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in text:
                errors.append(
                    f"Missing safety-critical implementation in {relative}: "
                    f"{fragment}"
                )

    forbidden_tools = (
        "close_performance_check.py",
        "closing_profile_check.py",
        "fast_exit_check.py",
        "grid_scroll_check.py",
        "sidebar_loading_spacing_check.py",
        "sidebar_polish_check.py",
    )
    for name in forbidden_tools:
        if (PACKAGE_ROOT / "tools" / name).exists():
            errors.append(f"Obsolete narrow diagnostic remains: {name}")

    tracked_caches = tracked_python_cache_files()
    if tracked_caches:
        errors.append(
            "Generated Python cache files are tracked by Git: "
            f"{tracked_caches[:5]}"
        )

    local_caches = local_python_cache_paths()

    source_manifest_path = PACKAGE_ROOT / "SOURCE_MANIFEST.sha256"
    manifest_entries: dict[str, str] = {}
    if source_manifest_path.is_file():
        for raw_line in source_manifest_path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            try:
                digest, relative = raw_line.split("  ./", 1)
            except ValueError:
                errors.append("Invalid SOURCE_MANIFEST.sha256 line")
                continue
            relative_path = Path(relative)
            if (
                len(digest) != 64
                or not relative
                or relative_path.is_absolute()
                or ".." in relative_path.parts
            ):
                errors.append("Unsafe or invalid SOURCE_MANIFEST.sha256 entry")
                continue
            manifest_entries[relative_path.as_posix()] = digest

        expected_source_files: set[str] = set()
        for path in SOURCE_ROOT.rglob("*"):
            if not path.is_file() or path == source_manifest_path:
                continue
            if is_generated_area(path) or is_python_cache_path(path):
                continue
            expected_source_files.add(path.relative_to(SOURCE_ROOT).as_posix())

        if set(manifest_entries) != expected_source_files:
            missing = sorted(expected_source_files - set(manifest_entries))
            stale = sorted(set(manifest_entries) - expected_source_files)
            errors.append(
                "Source manifest file set mismatch; "
                f"missing={missing[:2]}, stale={stale[:2]}"
            )
        for relative, expected_digest in manifest_entries.items():
            source = SOURCE_ROOT / relative
            if source.is_file() and sha256(source) != expected_digest:
                errors.append(f"Source manifest checksum mismatch: {relative}")

    secret_pattern = re.compile(
        r"(?i)(api[_-]?key|access[_-]?token|client[_-]?secret|private[_-]?key)\s*[:=]\s*['\"][^'\"]+"
    )
    for path in ROOT.rglob("*"):
        if is_generated_area(path):
            continue
        if not path.is_file() or path.suffix.lower() in {".png", ".ico", ".zip"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if secret_pattern.search(text):
            errors.append(f"Possible committed secret in {path.relative_to(ROOT)}")

    if errors:
        print("Release check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    if local_caches:
        print(
            "Notice: ignoring locally generated Python cache paths "
            f"({len(local_caches)} found; covered by .gitignore)."
        )

    print(f"Python Lair {EXPECTED_VERSION} release check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
