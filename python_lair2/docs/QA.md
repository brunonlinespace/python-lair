# Python Lair QA Guide

## Bug report essentials

Include:

- Python Lair version
- source/portable or AppImage
- distribution and version
- desktop environment
- X11 or Wayland
- exact reproduction steps
- expected and actual behavior
- terminal output or traceback

## High-value regression sequences

### Large full-document Paste

1. Open a script with 600 or more lines.
2. Select All and Copy.
3. Open another script.
4. Select All and Paste.
5. Wait, edit again, and switch pages.

The application must remain stable.

### Direct subfolder import

1. Drop an external `.py` file onto a nested sidebar folder.
2. Repeat with a naming conflict and choose Keep Both.
3. Confirm both files exist in that same nested folder.

### Repeated internal moves

Move one script repeatedly between several folders, including a same-folder
drop. No duplicates, stale tree items, disappearance, or crash should occur.

### Terminal lifecycle

Test a long-running TUI script:

- Terminal opens and running state appears.
- Stop ends the script and closes the terminal.
- Force Stop ends a hung script and closes the dedicated terminal.

### Large-workspace layout

- Switch List/Grid repeatedly.
- Scroll to the final Grid row; no List-sized blank region should remain.
- Resize the sidebar with hundreds or thousands of cards.
- Launch a script in Grid View; scroll position must not jump.

### Clean shutdown

Close during initial scan, after scan, with an editor open, and with a running
script. Unsaved prompts must preserve data when cancelled or closed via X.

## Suite Pythoine identity/provenance gate

| ID | Area | Procedure | Expected result |
|---|---|---|---|
| SUP-01 | Source | Inspect `python_lair2/python-lair.json`. | Name `Python Lair`, ID `python-lair`, version `2.1.1`, publisher `brunonlinespace`, desktop ID `io.github.brunonlinespace.python_lair`. |
| SUP-02 | Source | Inspect extracted root. | Root contains locked `README.md`, `main.py`, `suite-pythoine-component.json`, and `python_lair2/`. |
| SUP-03 | QA | Run `python3 python_lair2/tools/release_check.py`. | Identity and `SOURCE_MANIFEST.sha256` validation pass. |
| SUP-04 | Build | Start Fedora AppImage build. | Builder rejects missing/mismatched identity/source manifests before venv/build work. |
| SUP-05 | Provenance | Inspect `.build-info.txt`. | Main/source/project manifest, requirements, builder and output SHA-256 values are present. |

## Experimental r1.5.6 — Suite identity verification

| ID | Area | Procedure | Expected result |
|---|---|---|---|
| ID-01 | Portable | Run `python3 main.py --version` without importing PyQt6. | Exit 0; exact stdout is `Python Lair 2.1.1`. |
| ID-02 | Package | Inspect `python_lair2/__init__.py`. | APP_NAME=`Python Lair`, APP_ID=`python-lair`, APP_VERSION=`2.1.1`, publisher/desktop IDs match the JSON manifest. |
| ID-03 | Branding | Launch normally and open About. | Visible product branding remains `Python Lair 2`; no Suite identity wording leaks into the GUI. |
| ID-04 | Release gate | Run `python3 python_lair2/tools/release_check.py`. | Package identity, JSON identity, exact portable probe and source manifest all pass. |

