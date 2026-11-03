# Changelog

## [2.1.1] — 2026-11-03

### Publication and packaging

- Added the approved public-facing `README.md` at source root for the GitHub front page.
- Locked root README content in release QA so only release-version references may change unless an explicit content revision is approved.
- Updated the Fedora AppImage builder only as required to recognize, validate, package, and record provenance for the new root README.
- No application UI, runtime, workspace, editor, process-management, dependency, or feature behavior changed.

## [2.1.0] — 2026-09-24

### Packaging and presentation

- Promoted the substantial post-2.0.0 work already present in the development baseline to public version 2.1.0.
- Aligned the portable/AppImage structure with the current Suite Pythoine component contract.
- Hardened the Fedora AppImage builder without changing Python Lair-specific runtime behavior or dependencies.
- Brought About into current Plus-family presentation and changed the slogan to **Friendly. Fast. Focused.**

All notable public changes to Python Lair are documented here.

## [2.0.0] — 2026-08-03

First public stable release.

### Added

- Responsive background discovery of large Python-script workspaces
- Main Dashboard with persistent List and Grid presentations
- Search and sorting by title, creation time, and modification time
- Recursive sidebar navigation and folder mini-dashboards
- Direct external `.py` drops into the workspace root and target subfolders
- Internal drag-and-drop movement between workspace folders
- New Script, New Folder, Duplicate, Rename, Remove, and executable controls
- Embedded Python editor with line numbers and syntax highlighting
- Undo, Redo, Find, Replace, Replace All, Go to Line, Copy, Paste, and Select All
- Launch, Run in Terminal, Stop, and Force Stop
- External editor, file manager, terminal, browser, and project-link integration
- First-run workspace assistant
- Portable source layout and Fedora-oriented AppImage build pipeline
- Bundled application, folder, script, and Dashboard assets
- GPL-3.0-or-later licensing

### Performance

- One asynchronous traversal supplies scripts, folders, and watcher paths
- Persistent Dashboard cards avoid rebuilding on view changes
- Runtime-only state changes no longer reorder the entire Dashboard
- Rubber-band sidebar resizing avoids repeated large-grid relayouts
- Grid scroll extent follows the active page instead of the taller List View
- Demonstrated with a workspace containing approximately 2,640 scripts

### Reliability

- Atomic repository path changes prevent duplicate sidebar entries after rename
- Repeated drag-and-drop movement preserves live Qt items and module state
- Same-folder drops are harmless no-ops
- Workspace Refresh rebuilds stale navigation state
- AppImage-safe host Python and desktop-application launching
- Tracked external-terminal sessions with Stop and Force Stop support
- Safe Select All and large full-document Paste handling
- Clamped, exception-safe bracket highlighting
- Replace All uses the same hardened full-document replacement path
- Atomic UTF-8 saves preserve executable permissions
- Cooperative workspace-scan cancellation during shutdown
- Visible responsive closing feedback
- Unsaved-change dialogs default safely to preserving editor contents
- Rich-text editor headers escape filenames and paths safely
- Dashboard rich-text labels escape filesystem-derived names safely
- Closing a move-conflict dialog never replaces a file implicitly
- Workspace and configuration write probes use unique temporary files

### Packaging

- Runtime-resolved bundled assets
- AppImage desktop entry and AppStream metadata
- SHA-256 generation in the Fedora build script
- Complete static release validation and GitHub contribution templates

### Development history

Pre-release development used several internal version labels. None were
published. Their completed work was consolidated into this first public 2.0.0
release.

### Packaging correction before publication

- Generalized the AppImage helpers for Fedora 43 and Fedora 44.
- Run source validation before creating the build virtual environment.
- Exclude generated build environments and ordinary ignored Python caches from
  working-tree failures while still rejecting cache files tracked by Git.
- Prevent accidental root-owned AppImage builds by rejecting `sudo` execution
  unless a controlled CI/container explicitly sets `ALLOW_ROOT_BUILD=1`.
- Record the Python, PyQt6/Qt, PyInstaller, and build-host versions next to the
  generated AppImage.
