# Python Lair 2 Architecture

## Repository layout

```text
source-root/
├── main.py
└── python_lair2/
    ├── app.py
    ├── app_constants.py
    ├── assets/
    ├── controllers/
    ├── docs/
    ├── models/
    ├── packaging/
    ├── services/
    ├── tools/
    ├── widgets/
    ├── LICENSE
    └── requirements.txt
```

## Startup

1. `main.py` creates `QApplication` and application identity.
2. `RuntimePaths` detects source, frozen, or AppImage execution.
3. `ConfigService` loads writable user settings.
4. A fresh installation may show `FirstRunWizard`.
5. A writable workspace is selected and validated.
6. `MainWindow` paints immediately.
7. `FilesystemWatcher` launches one background `ModuleScanner` traversal.
8. The snapshot updates folder nodes, repository modules, and watcher paths.

## Data layer

### `Module`

Stores filesystem metadata and runtime state for one Python script.

### `ModuleRepository`

The authoritative collection. It normalizes paths, preserves canonical Module
objects, searches, sorts, and emits incremental Qt signals.

### `ModuleStateStore`

Associates a module path with live UI/process references without placing Qt
objects in the pure data model.

## Services

### `RuntimePaths`

Resolves assets, writable configuration, and runtime-appropriate workspace
locations without relying on the shell working directory.

### `RuntimeLauncher`

Selects host Python and launches terminals, editors, file managers, and URLs.
Bundled runtime variables are removed before host programs start.

### `ModuleScanner`

Performs one iterative traversal, applies default and user ignore rules, avoids
directory symlinks, and supports cooperative cancellation.

### `FilesystemWatcher`

Runs scanning in a QThread, debounces changes, caps native directory watches,
and joins an active worker safely during shutdown.

### `ProcessManager`

Owns managed QProcess scripts and tracked external-terminal sessions, including
running state, Stop, Force Stop, output draining, and shutdown cleanup.

### `ConfigService`

Reads and atomically replaces a small JSON preferences file.

## Controllers

### `FileActionsController`

Owns safe filesystem mutations and import conflict resolution. Repository
signals update the UI after successful operations.

### `EditorManager`

Owns the Dashboard, folder pages, editor pages, page switching, and unsaved
page-close decisions.

## Widgets

### `MainWindow`

Composes menus, navigation, content stack, services, status, startup scan, and
clean shutdown.

### `NavigationWidget`

Persistent Dashboard destination, folder tree, expand/collapse controls, and
internal/external drag-and-drop targets.

### `DashboardWidget`

Maintains separate persistent List and Grid cards. `CurrentPageStack` reports
only the active page's scroll height.

### `FolderDashboard`

Folder-specific script search, actions, and direct external `.py` imports.

### `CodeEditor` / `EditorPage`

Provide the text editor, line numbers, Python highlighting, defensive bracket
matching, hardened whole-document replacement, disk-change detection, and
atomic UTF-8 save.

## Runtime modes

### Source/portable

- Entry: `python main.py`
- Default workspace: `./my library`
- User scripts use the current interpreter/virtual environment.

### AppImage/frozen

- Bundle is read-only.
- Workspace is external and writable.
- User scripts use host `python3`.
- Host applications receive a sanitized environment.

## Shutdown contract

1. Ask about unsaved editors.
2. Save UI and workspace preferences.
3. Show closing feedback.
4. Cancel and join an active scan.
5. Stop managed scripts and terminal sessions.
6. Exit only after these safety prerequisites complete.

The operating system may reclaim remaining GUI-only objects directly because a
workspace with thousands of scripts owns thousands of cards and tree items.
