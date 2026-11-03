# Python Lair 2 — Project Memory

Use this file to restore project context in a future development session.

## Public identity

- **Name:** Python Lair 2
- **Public version:** 2.1.1
- **Window title:** Python Lair 2 — Lightweight Python IDE
- **License:** GPL-3.0-or-later
- **Repository:** https://github.com/brunonlinespace/python-lair
- **Toolkit:** PyQt6
- **Primary platform:** Linux
- **Primary binary format:** AppImage, native x86_64/aarch64

## Product purpose

Python Lair is a focused desktop application for users who maintain large
personal libraries of standalone Python scripts. It is not intended to replace
PyCharm or Visual Studio Code.

The application has been stress-tested with approximately 2,640 scripts.

## Stable capabilities

- portable and AppImage-aware runtime paths
- first-run workspace assistant
- asynchronous cancellable workspace scanning
- List and Grid Dashboard views
- search and sorting
- recursive sidebar and folder mini-dashboards
- direct external `.py` drops into target folders
- internal script movement between folders
- script/folder creation, rename, duplication, removal, and permissions
- embedded editor and safe full-document replacement
- Launch, Terminal, Stop, and Force Stop
- host editor, file manager, terminal, browser, and URL integration
- visible startup and shutdown feedback

## Important architecture

```text
main.py
  ├─ RuntimePaths / ConfigService / FirstRunWizard
  └─ MainWindow
       ├─ ModuleRepository / ModuleStateStore
       ├─ ModuleScanner / FilesystemWatcher
       ├─ RuntimeLauncher / ProcessManager
       ├─ FileActionsController / EditorManager
       └─ Navigation / Dashboard / FolderDashboard / EditorPage
```

## Critical design decisions

1. **One source tree, multiple runtime modes**
   - Source mode uses the interpreter that launched `main.py`.
   - AppImage mode uses a host `python3` for user scripts.
   - Host applications are launched through `RuntimeLauncher` with a sanitized
     environment.

2. **Application and user workspace are separate**
   - Source default: `./my library`
   - AppImage default: `~/Documents/Python Lair Workspace`
   - AppImage contents are treated as read-only.

3. **Scanning never blocks startup**
   - One worker traversal supplies scripts, folders, and watcher paths.
   - Cancellation is checked at directory and filesystem-entry boundaries.
   - A live QThread must never be destroyed.

4. **Dashboard presentations are persistent**
   - List and Grid have separate card instances.
   - Switching view is a stack-page change.
   - Running/dirty updates do not rebuild all card layouts.

5. **Terminal sessions are owned and tracked**
   - A helper is materialized in writable config storage.
   - Stop is graceful; Force Stop closes the terminal and child group.
   - Konsole uses `--nofork` for a dedicated manageable process.

6. **Editor decorations are defensive**
   - Cursor positions are clamped before bracket indexing.
   - Decoration exceptions cannot abort Qt.
   - Full-document Paste and Replace All use the hardened replacement path.

7. **Shutdown safety precedes fast exit**
   - Unsaved edits are resolved.
   - Configuration is saved.
   - Scanner and managed processes are stopped.
   - Only then may the process bypass expensive GUI-object destruction.
   - Shutdown profiling is opt-in with `PYTHON_LAIR_PROFILE_SHUTDOWN=1`.

## Bugs that must not return

- launching the AppImage itself instead of a user script
- relying on host emoji fonts for application icons
- repeated full scans during startup
- destroying a running QThread
- rebuilding every Dashboard card for a running-state change
- reparenting one card between List and Grid layouts
- assuming bundled modules exist as ordinary `.py` files
- indexing document text with an unclamped cursor position
- blindly honoring `$EDITOR` when it points to a terminal editor
- Keep Both imports placing a subfolder copy in the workspace root
- closing an unsaved-change dialog via X being treated as Discard
- Replace All bypassing full-document editor safeguards
- rendering unescaped filenames or paths as rich text
- closing a move conflict dialog being treated as Replace
- using fixed temporary filenames for workspace/configuration probes

## Internal version history

Pre-release development temporarily used 2.1.0 and 2.1.1 labels. Those builds
were never published. Their direct-folder import and final layout work were
consolidated into the first public 2.0.0 release.

## Resume instructions

Provide this file, `ARCHITECTURE.md`, `ROADMAP.md`, and the latest source tree,
then say:

> Continue Python Lair from public version 2.1.1. Read the project memory,
> architecture, and roadmap before changing code. Preserve the documented
> invariants and do not reintroduce known regressions.

## AppImage build privilege and cache rule

`python_lair2/packaging/fedora/build-appimage.sh` must normally run as the desktop user, not
through `sudo`. The dependency installer invokes `sudo dnf` internally.
Working-tree `__pycache__` and `.pyc` files are ordinary ignored artifacts and
must not block packaging; `release_check.py` rejects them only if Git reports
that they are tracked. Controlled root-based containers may opt in with
`ALLOW_ROOT_BUILD=1`.
