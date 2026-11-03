# Python Lair 2

**Python Lair 2 — Lightweight Python IDE** is a Linux desktop application for
organizing, browsing, editing, and launching large personal collections of
Python scripts.

Python Lair is deliberately lighter and more focused than a full project IDE.
It is designed for users who maintain many standalone utilities and want one
fast workspace for finding, editing, moving, and running them.

## Highlights

- Responsive background scanning for large workspaces
- Tested with more than 2,600 Python scripts
- Persistent List and Grid Dashboard views
- Search and sorting by title, creation time, or modification time
- Recursive workspace sidebar and folder mini-dashboards
- Direct external `.py` drops into the workspace root or target subfolders
- Internal drag-and-drop movement between workspace folders
- Embedded Python editor with line numbers and syntax highlighting
- Undo, Redo, Find, Replace, Replace All, Go to Line, Copy, Paste, and Select All
- Script creation, duplication, rename, removal, and executable permissions
- Launch, Run in Terminal, Stop, and Force Stop
- External editor, file manager, browser, and terminal integration
- Portable source mode and AppImage-aware runtime behavior
- First-run workspace assistant
- Cooperative scan cancellation and visible clean-shutdown feedback

## Requirements

- Linux on native x86_64 or aarch64 for the supplied AppImage builder
- Python 3.10 or newer for source mode
- PyQt6 6.6 or newer, below PyQt7
- A host `python3` installation for running user scripts from the AppImage

## Run from source

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r python_lair2/requirements.txt
python main.py
```

Source mode uses `my library/` beside `main.py` as its default workspace. The
first-run assistant can choose a different folder.

To show the assistant again:

```bash
python main.py --setup
```

To display the version without opening the interface:

```bash
python main.py --version
```

## AppImage

Make the AppImage executable and run it:

```bash
chmod +x Python-Lair-2.1.1-x86_64.AppImage
./Python-Lair-2.1.1-x86_64.AppImage
```

AppImage mode stores user scripts outside the read-only bundle. The recommended
default is `~/Documents/Python Lair Workspace`.

The AppImage launches user scripts with the host `python3`, not its bundled
application runtime. Override the interpreter when required:

```bash
PYTHON_LAIR_PYTHON=/path/to/python3 ./Python-Lair-2.1.1-x86_64.AppImage
```

Force a particular graphical editor with:

```bash
PYTHON_LAIR_EDITOR="kate" ./Python-Lair-2.1.1-x86_64.AppImage
```

## Core workflows

### Import directly into a folder

Drag one or several external `.py` files onto:

- the pinned **Dashboard** destination for the workspace root;
- a folder row in the sidebar; or
- any folder mini-dashboard.

External drops copy files. Internal Python Lair card/tree drags move files.
Filename conflicts offer Replace, Keep Both, or Skip.

### Stop scripts

- **Stop** requests graceful termination.
- **Force Stop** immediately ends the managed script session.
- Terminal sessions are tracked so their running state and terminal window can
  be closed by Python Lair.

### Large workspaces

Scanning runs outside the GUI thread and skips common heavy directories such as
`.git`, virtual environments, caches, `node_modules`, `build`, and `dist`.
Additional workspace-specific exclusions can be added to `.python-lair-ignore`.
See `.python-lair-ignore.example`.

## Configuration and diagnostics

Configuration is stored through Qt's standard per-user application-config
location, normally under `~/.config/python-lair-2/` on Linux.

Shutdown timing diagnostics are opt-in:

```bash
PYTHON_LAIR_PROFILE_SHUTDOWN=1 python main.py
```

When enabled, timing records are written to `shutdown-timing.jsonl` in the
application configuration directory and printed to the launching terminal.

## Release checks

The comprehensive static release check does not require PyQt6 or a display:

```bash
python -m python_lair2.tools.release_check
```

Additional focused checks are available under `python_lair2/tools/`. The manual
acceptance procedure is documented in `QA.md` and `RELEASE_CHECKLIST.md`.

## Building the AppImage

The shared Fedora 43/44 build scripts are under `python_lair2/packaging/fedora/`:

```bash
./python_lair2/packaging/fedora/install-build-deps.sh
./python_lair2/packaging/fedora/build-appimage.sh
```

Run both commands from your normal user account. The dependency helper invokes
`sudo dnf` internally; do not prefix the build command with `sudo`.

See `BUILDING.md` and `packaging/README.md`. The same source should be tested on
multiple desktop environments; the build desktop must not become an application
requirement.

## Project documentation

- `CHANGELOG.md` — public release history
- `RELEASE_NOTES.md` — highlights for the current release
- `ARCHITECTURE.md` — internal structure and runtime design
- `PROJECT_MEMORY.md` — decisions and regression history for future work
- `ROADMAP.md` — planned development
- `CONTRIBUTING.md` — contribution workflow
- `SECURITY.md` — private vulnerability reporting
- `QA.md` — manual acceptance testing

## License

Python Lair 2 is licensed under the GNU General Public License version 3 or
later (`GPL-3.0-or-later`). See `LICENSE`.

## Links

- Repository: https://github.com/brunonlinespace/python-lair
- Issues: https://github.com/brunonlinespace/python-lair/issues
