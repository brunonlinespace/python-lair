<p align="center">
  <a href="https://github.com/brunonlinespace/python-lair">
    <img
      src="python_lair2/assets/icons/python-lair-2.png"
      alt="Python Lair 2"
      width="256"
    >
  </a>
</p>

# Python Lair 2

**Friendly. Fast. Focused.**

Python Lair 2 is a lightweight Python IDE and script launcher for Linux, built for organizing, browsing, editing, and running large personal collections of standalone Python scripts. It combines an ordinary-folder workspace, recursive navigation, List and Grid dashboards, focused source editing, and practical runtime controls while continuing to work directly with normal `.py` files.

Current release: **2.1.1**

Repository: <https://github.com/brunonlinespace/python-lair>

## What Python Lair 2 is

Python Lair 2 is designed for people who maintain many standalone Python utilities and want one fast place to find, edit, organize, and launch them without adopting the weight or project model of a full development environment.

A workspace is an ordinary folder containing Python scripts and subfolders. Python Lair does not introduce a private script format, database, or project container. Only the active workspace is scanned and watched.

Python Lair discovers ordinary `.py` scripts recursively. `__init__.py` files are deliberately excluded from Dashboard/script discovery so package markers do not become launcher entries.

## Highlights

- Responsive background scanning for large Python-script workspaces.
- **My Nest** sidebar with Dashboard access, recursive folders, expandable navigation, and folder mini-dashboards.
- Workspace **Dashboard** with persistent List and Grid views, live search, Refresh, and sorting by title, creation time, or modification time.
- Direct external `.py` import into the workspace root or chosen subfolders.
- Internal drag-and-drop movement between workspace folders.
- Embedded Python source editor with syntax highlighting, line numbers, Find/Replace, Go To Line, comment toggling, and line/selection duplication.
- Persistent Word Wrap, Line Numbers, display-font, status-bar, workspace, Dashboard-view, and runtime preferences.
- Session-local **View Only** editing protection.
- Python-source encoding detection with BOM and PEP 263 handling, newline preservation, and bounded file loading.
- Script **Properties** including path, permissions, executable state, lines, characters, encoding, newline style, View Only state, and Insert/Overwrite mode.
- Run normally, **In Terminal**, **As Administrator in Terminal**, or **Run with Arguments**.
- Selectable interpreter, working-directory control, and reusable environment profiles.
- **Syntax / Lint Check**, executable-permission control, Stop, and Force Stop.
- External editor, containing-folder, file-manager, browser, and terminal integration.
- First-run workspace assistant plus source, frozen-bundle, and AppImage-aware runtime paths.
- Hardened Fedora 43/44 AppImage build tooling with release validation, checksums, and build provenance.

## Interface

### AppMenu

The native application menu is the primary command surface and is organised around Python Lair's script-workspace workflow.

- **File** — New Script, New Folder, Import Script(s), workspace selection, current-folder actions, Save, Duplicate, Properties, and Exit.
- **Edit** — Undo/Redo, clipboard operations, Toggle Comment, Duplicate Line or Selection, Find/Replace, Go To Line, and Preferences.
- **View** — Dashboard, List/Grid view, Sidebar, Full Screen, View Only, Word Wrap, Line Numbers, Display Font, and Status Bar.
- **Run** — Run Script, terminal/admin launch, arguments, Syntax/Lint Check, interpreter, working directory, environment profiles, Stop/Force Stop, and executable permissions.
- **Help** — documentation, Keyboard Shortcuts, GitHub, issue reporting, and About.

The same editor/runtime actions are also exposed contextually from the embedded editor where appropriate.

### Dashboard and My Nest

The Dashboard is the main overview of the active workspace.

- **New Script** and **New Folder** remain on the left of the Dashboard command row.
- **Refresh**, the dynamic **Grid View / List View** toggle, and the sort selector remain right-aligned.
- Search filters scripts by title or filename.
- List and Grid cards expose Edit, Launch, and Terminal actions; Stop and Force Stop appear while a script is running.
- Script cards show filename/location, modification time, file size, executable state, unsaved state, and running state.

The **My Nest** sidebar keeps Dashboard pinned above the recursive folder tree. Expand All / Collapse All controls sit above the tree, and folder pages provide their own search, creation, external-folder, terminal, rename, remove, and import workflows.

## Workspaces

Python Lair keeps the workspace as an ordinary filesystem folder.

- **New Workspace...** creates a new workspace folder and stores it for the next launch.
- **Open Workspace...** selects an existing folder for the next launch.
- **Preferences...** can change the workspace location or schedule the Setup Assistant for the next start.
- Source mode defaults to `my library/` beside `main.py` unless another workspace is selected.
- Frozen/AppImage mode defaults to `~/Documents/Python Lair Workspace` unless configured otherwise.
- Only the active workspace is scanned and watched.
- Common heavy directories such as `.git`, virtual environments, caches, `node_modules`, `build`, and `dist` are ignored automatically.
- Additional workspace-specific exclusions can be placed in `.python-lair-ignore`; see `.python-lair-ignore.example`.

Workspace changes selected from the running application take effect on the next start.

### Import and drag and drop

Python Lair deliberately treats external files as imports into the managed workspace.

- **Import Script(s)...** copies one or more external `.py` files into the active workspace.
- Dropping external `.py` files onto the root Dashboard imports them into the workspace root.
- Dropping external `.py` files onto sidebar-folder or folder-dashboard targets imports them directly into that folder.
- Dragging managed script cards/tree entries onto workspace folders moves the existing script instead of importing another copy.
- Filename conflicts are resolved explicitly rather than silently replacing an unrelated script.

## Editing

Python Lair's embedded editor is focused on ordinary Python source files.

Editing includes:

- Python syntax highlighting;
- line numbers;
- configurable display font and tab width;
- Word Wrap;
- View Only mode;
- Insert / Overwrite mode;
- Undo and Redo;
- Cut, Copy, Paste, Delete, and Select All;
- Toggle Comment;
- Duplicate Line or Selection;
- Find, Find Previous/Next, Replace, and Replace All;
- Go To Line;
- Properties.

Python source decoding honours BOMs and recognised PEP 263 encoding declarations. If a source file cannot be decoded using the normal Python rules, Python Lair can offer explicit fallback encodings. Saving preserves the selected encoding, BOM where applicable, newline style, and existing file permissions.

New scripts are ordinary `.py` files created directly inside the active workspace or selected folder.

## Running scripts

Python Lair combines source editing with a managed script-runtime layer.

- **Run Script** launches the active script directly.
- **Run in Terminal** opens it in an external terminal.
- **Run as Administrator in Terminal** uses the elevated terminal workflow.
- **Run with Arguments...** parses user arguments without invoking an intermediate shell.
- **Select Interpreter...** can override the default Python interpreter.
- **Working Directory...** can use the script folder or a chosen custom directory.
- **Environment Profiles...** provide reusable sets of environment variables.
- **Syntax / Lint Check** provides a focused source-validation path.
- **Make Executable / Remove Executable** updates the script's executable permission.
- **Stop** requests graceful termination.
- **Force Stop** immediately terminates the managed script session.

Terminal sessions are tracked so Python Lair can reflect running state and stop the associated managed terminal process when requested.

In AppImage mode, user scripts run with the host Python interpreter rather than the bundled application runtime. Override it when necessary with:

```bash
PYTHON_LAIR_PYTHON=/path/to/python3 ./Python-Lair-2.1.1-x86_64.AppImage
```

A preferred external editor can likewise be supplied with:

```bash
PYTHON_LAIR_EDITOR="kate" ./Python-Lair-2.1.1-x86_64.AppImage
```

## File safety and source fidelity

Python Lair treats source-file integrity as part of the normal editor lifecycle.

File loading uses bounded regular-file reads and rejects unstable, oversized, or binary-looking content. Open files retain a disk snapshot so external changes can be detected rather than silently ignored.

Saves are staged through synchronized temporary files. Before replacing an existing file, Python Lair verifies that the path and backing file still match the state that was opened. If a source changes externally while unsaved editor changes exist, Python Lair warns before replacing the newer disk version.

The editor also preserves source encoding, BOM, newline style, and file mode across ordinary saves.

## Useful keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+N` | New Script |
| `Ctrl+Shift+N` | New Folder |
| `Ctrl+O` | Import Script(s) |
| `Ctrl+S` | Save current script |
| `Ctrl+Shift+D` | Duplicate current script |
| `Ctrl+X` / `Ctrl+C` / `Ctrl+V` | Cut / Copy / Paste |
| `Ctrl+F` | Find |
| `F3` / `Shift+F3` | Find next / previous |
| `Esc` | Clear embedded-editor search |
| `Ctrl+H` | Find and Replace |
| `Ctrl+G` | Go To Line |
| `Ctrl+/` | Toggle Comment |
| `Ctrl+D` | Duplicate Line or Selection |
| `Ctrl+Alt+D` | Show Dashboard |
| `F5` | Run Script |
| `Shift+F5` | Stop Script |
| `Ctrl+Shift+F5` | Force Stop Script |
| `Ctrl+Shift+T` | Run in Terminal |
| `Ctrl+Alt+Shift+T` | Run as Administrator in Terminal |
| `Ctrl+Shift+R` | Run with Arguments |
| `Ctrl+Shift+L` | Syntax / Lint Check |
| `Ctrl+Alt+X` | Make / Remove Executable |
| `F11` | Full Screen |
| `F1` | Documentation |

The complete live shortcut inventory is available from **Help → Keyboard Shortcuts**.

## Running from source

Python Lair 2 requires Python 3.10 or newer and PyQt6 6.6 or newer within the supported PyQt6 6.x series.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r python_lair2/requirements.txt
python main.py
```

Other useful launch forms:

```bash
python main.py --version
python main.py --setup
```

The source/portable layout keeps `main.py` at the project root and the application in `python_lair2/`.

## Building the AppImage

Fedora 43/44 build helpers are included in the source tree:

```bash
./python_lair2/packaging/fedora/install-build-deps.sh
./python_lair2/packaging/fedora/build-appimage.sh
```

Expected outputs include:

```text
python_lair2/dist/Python-Lair-2.1.1-x86_64.AppImage
python_lair2/dist/Python-Lair-2.1.1-x86_64.AppImage.sha256
python_lair2/dist/Python-Lair-2.1.1-x86_64.build-info.txt
python_lair2/dist/Python-Lair-2.1.1-x86_64.build-python-lock.txt
```

The builder supports native `x86_64` and `aarch64` Fedora hosts. Run the AppImage builder as the normal desktop user. The dependency helper may invoke `sudo dnf`; the builder itself should not normally be run with `sudo`.

## Validation

Run the authoritative source-release gate with:

```bash
python -m python_lair2.tools.release_check
```

Additional focused checks cover UI layout, direct drag/drop, runtime launch paths, external-editor integration, clean shutdown, acceptance routing, terminal Force Stop, Sheepy-derived editor/runtime behavior, sorting, and source/runtime path contracts.

The source release also carries `SOURCE_MANIFEST.sha256` for release-tree integrity.

## Configuration

Python Lair stores application configuration outside the workspace through Qt's per-user application configuration location, normally under `~/.config/python-lair-2/` on Linux.

The active configuration file is `python_lair_2_config.json`. Workspace scripts remain ordinary `.py` files and are never embedded into application configuration.

The workspace location can also be overridden for a launch with:

```bash
PYTHON_LAIR_WORKSPACE=/path/to/workspace python main.py
```

Shutdown timing diagnostics are opt-in:

```bash
PYTHON_LAIR_PROFILE_SHUTDOWN=1 python main.py
```

## Scope

Python Lair 2 is a **Python-script workspace, editor, organizer, and launcher**. It deliberately focuses on collections of ordinary standalone `.py` files rather than trying to replace a full project IDE.

The application keeps scripts directly on disk, uses an ordinary folder as its workspace boundary, and does not require a private project/database format. Its Suite Pythoine identity is an **Extension** with no generic document-routing claim.

## License

Python Lair 2 is licensed under the **GNU General Public License v3.0 or later**.

See `python_lair2/LICENSE` for the complete license text.

## Links

- Python Lair: <https://github.com/brunonlinespace/python-lair>
- Issues: <https://github.com/brunonlinespace/python-lair/issues>
- GitHub profile: <https://github.com/brunonlinespace/>

Copyright © 2026 Bruno Machado.
