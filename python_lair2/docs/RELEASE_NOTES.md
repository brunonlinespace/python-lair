# Python Lair 2.1.1 — locked GitHub README publication update

Python Lair 2.1.1 is a publication/source-packaging release only. Application behavior is unchanged from 2.1.0.

- adds the approved public-facing `README.md` at source root for the GitHub repository front page;
- treats that root README as locked content: future releases may update version-number references only unless a content change is explicitly approved;
- updates source-release QA to require the four-item root and enforce the README content lock;
- updates the Fedora AppImage builder only as necessary to require the root README, install it as packaged documentation, and record its SHA-256 provenance;
- advances package, Suite, desktop, AppStream, build, QA, and release identity to `2.1.1`;
- makes no application UI, editor, workspace, runtime, process, dependency, or feature changes.

# Python Lair 2.1.0 — Plus-family/About and AppImage packaging alignment

Python Lair 2.1.0 promotes the substantial post-2.0.0 application work accumulated in the development line. This release pass does not redesign Python Lair behavior; it aligns packaging with the current Pythoine family contract and brings About back into the current Plus-family presentation.

- synchronizes public/package/build identity to `2.1.0`;
- adds the root Suite Pythoine component manifest while preserving Python Lair as an Extension with no document routing;
- moves pinned PyInstaller requirements to `packaging/pyinstaller/build-requirements.txt`;
- upgrades the Fedora AppImage builder to the hardened non-privileged Fedora 43/44, native x86_64/aarch64 contract;
- adds safe build-root cleanup, pip validation/lock, metadata validation, controlled appimagetool acquisition, checksums and build provenance, and finished-AppImage version testing;
- keeps Python Lair-specific Qt/runtime behavior and existing PyInstaller dependency choices unchanged;
- aligns About to the Plus-family 700×470 presentation, Configuration label and `Friendly. Fast. Focused.` slogan.

# Python Lair 2 experimental r1.5.6 — Suite identity probe fix

This packaging/identity hotfix retains all r1.5.5 application behavior and visible
Python Lair 2 branding.

- canonical package identity is now exported dependency-free from
  `python_lair2/__init__.py` as `Python Lair` / `python-lair` / `2.0.0`;
- publisher and desktop IDs are exported beside that identity;
- visible GUI branding remains `Python Lair 2`;
- root `main.py --version` is handled before importing PyQt6 and returns exactly
  `Python Lair 2.0.0`;
- frozen/AppImage `--version` returns the same exact identity;
- release QA now checks package ↔ JSON-manifest agreement and executes the
  dependency-free portable identity probe.

# Python Lair 2.0.0 experimental r1.5.5 — Suite Pythoine identity alignment

This experimental packaging refresh does not change Python Lair editor, runtime,
workspace, drag-and-drop, or process behavior.

- adds `python_lair2/python-lair.json` using the Pad-family/Suite identity schema;
- adds `python_lair2/SOURCE_MANIFEST.sha256` covering the complete portable source;
- release QA verifies manifest identity, file inventory and SHA-256 checksums;
- the Fedora AppImage builder requires both manifests before build work begins;
- AppImage build-info records `main.py`, source-manifest, project-manifest,
  requirements, builder and output SHA-256 provenance;
- the portable outer root remains exactly `main.py` + `python_lair2/`.

# Python Lair 2.0.0

Python Lair 2.0.0 is the first public stable release of the lightweight Linux
IDE and launcher for large personal Python-script libraries.

## Highlights

- Browse, search, sort, edit, and launch thousands of Python scripts
- Directly drop external `.py` files into the desired sidebar folder or folder
  mini-dashboard
- Move scripts internally through drag and drop
- Use persistent List and Grid Dashboard views
- Edit safely with hardened Select All, Paste, Replace All, Undo, and Redo
- Run scripts normally or in an external terminal
- Stop or Force Stop managed script sessions
- Use host editors, file managers, terminals, and browsers from the AppImage
- Choose a writable workspace through the first-run assistant
- Close cleanly while a large workspace scan is active

## Validated environments

Build helpers are provided for Fedora 43 and Fedora 44. Development and
acceptance testing included XFCE and KDE Plasma. AppImage behavior
must still be validated on each intended release target because the build
environment can affect bundled dependencies.

## Known characteristics

- Closing a workspace containing thousands of cards and tree items can take a
  short time. Python Lair displays closing feedback while it completes safe
  scanner and process cleanup.
- The official AppImage is currently x86_64.
- AppImage mode requires a host Python interpreter to run user scripts.

See `CHANGELOG.md` for the complete feature and reliability list.

## Packaging note

The source archive includes shared Fedora 43/44 AppImage build helpers. Static
source validation runs before the build environment is generated. Ordinary
local Python caches do not block a build; cache files are rejected only when
Git reports that they are tracked. Build the AppImage as the normal user rather
than through `sudo`.
