# Contributing to Python Lair

Thank you for helping improve Python Lair.

## Before changing code

Read `PROJECT_MEMORY.md`, `ARCHITECTURE.md`, and `ROADMAP.md`. Several unusual
implementation choices protect regressions found during large-workspace and
AppImage testing.

## Workflow

1. Open an issue for a substantial feature or behavior change.
2. Create a focused branch, such as `fix/editor-paste` or
   `feature/multi-select`.
3. Keep commits small and descriptive.
4. Run the static release check and relevant focused checks.
5. Perform the manual regression sequence in `QA.md`.
6. Submit a pull request explaining the problem, solution, and tested systems.

## Coding principles

- Keep the repository/models independent from widgets where practical.
- Route host application launching through `RuntimeLauncher`.
- Never block startup with a workspace traversal.
- Never destroy a running QThread.
- Preserve canonical Module and ModuleState objects during path changes.
- Treat user files and unsaved editor content conservatively.
- Avoid adding desktop-environment-specific dependencies.

## Generated files

Do not commit virtual environments, user workspaces, AppImages, PyInstaller
output, caches, timing logs, or local configuration. Release binaries belong in
GitHub Releases, not the Git history.

## License

Contributions are accepted under the project's GPL-3.0-or-later license.
