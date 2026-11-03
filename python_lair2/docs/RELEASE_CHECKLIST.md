# Python Lair 2.1.1 Release Checklist

## Static checks

- [ ] `python -m python_lair2.tools.release_check`
- [ ] `python -m python_lair2.tools.ui_layout_check`
- [ ] `python -m python_lair2.tools.shutdown_check`
- [ ] `python -m python_lair2.tools.direct_drop_check`
- [ ] `python -m python_lair2.tools.acceptance_route_check`
- [ ] `python -m python_lair2.tools.terminal_force_stop_check`
- [ ] `python -m python_lair2.tools.sort_check` in an environment with PyQt6
- [ ] `python main.py --version` reports `Python Lair 2.1.1`

## Source smoke test

- [ ] First-run assistant selects a workspace
- [ ] Large workspace loads without blocking the window
- [ ] Search and every sort mode work
- [ ] List/Grid switching is responsive
- [ ] Grid scroll ends after the final card
- [ ] Sidebar Dashboard remains selected and centered
- [ ] External `.py` drops import to root and target subfolders
- [ ] Keep Both creates the sibling copy in the target folder
- [ ] Internal moves and same-folder no-ops behave correctly
- [ ] New, Duplicate, Rename, Remove, and executable toggle work
- [ ] Save, Discard, Undo, Redo, Select All, Copy, Paste, and Replace All work
- [ ] Closing an unsaved prompt via X cancels the close
- [ ] Launch, Terminal, Stop, and Force Stop work
- [ ] External Editor, Open Folder, GitHub, Issues, and Documentation work
- [ ] Close during an active large scan is safe and displays feedback

## AppImage build and smoke test

- [ ] Build command is run as the normal desktop user, not with `sudo`
- [ ] Existing root-owned `build/` or `python_lair2/dist/` output has been removed
- [ ] App and all icons appear
- [ ] Writable external workspace is used
- [ ] User scripts launch with host Python
- [ ] Terminal window and running state are tracked
- [ ] Stop and Force Stop close the managed session
- [ ] Host editor, file manager, terminal, and browser open correctly
- [ ] Tested on Fedora XFCE and KDE Plasma
- [ ] `--appimage-extract-and-run --version` reports 2.1.1

## GitHub release

- [ ] Review `git status` and ensure no workspace/user files are staged
- [ ] Commit the public source
- [ ] Tag `v2.1.1`
- [ ] Build AppImage from the tagged commit
- [ ] Upload AppImage and `.sha256` to a GitHub Release
- [ ] Add screenshots, including the 2,640-script stress test
- [ ] Publish release notes from `RELEASE_NOTES.md`
