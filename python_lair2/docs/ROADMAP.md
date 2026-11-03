# Python Lair Roadmap

## 2.0.0 — First public stable release

Status: **Current release**

The 2.0 line establishes the stable workspace, editor, process-management,
portable, and AppImage foundation.

## 2.0.x — Maintenance

Suitable changes:

- crash and regression fixes
- compatibility and packaging corrections
- documentation fixes
- narrowly scoped performance improvements

## 2.1.0 — Bulk workflow and desktop integration

Candidate features:

- multi-selection of scripts
- moving or removing several selected scripts
- bulk executable-permission changes
- importing external folders while preserving structure
- Applications-menu installer and icon integration
- optional desktop shortcut management
- integration removal or repair from Preferences

## Later possibilities

- reproducible CI/container AppImage builds
- broader distribution and Wayland test matrix
- ARM64 AppImage
- multiple workspace profiles
- Git integration
- plugin API
- debugger or language-server support
- automated GUI regression tests

## Product boundary

Python Lair should remain a focused, lightweight manager and editor for large
collections of standalone Python scripts. Features that turn it into a heavy
general-purpose IDE should be evaluated carefully.
