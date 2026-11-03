# Building Python Lair 2

## Source environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r python_lair2/requirements.txt
python main.py
```

Python 3.10 or newer is recommended.

## Static release validation

```bash
python -m python_lair2.tools.release_check
```

This check deliberately avoids importing PyQt6, so it can run in a minimal CI
or packaging environment before dependencies are installed.

## Fedora 43 and Fedora 44 AppImage

```bash
./python_lair2/packaging/fedora/install-build-deps.sh
./python_lair2/packaging/fedora/build-appimage.sh
```

Run these from the normal desktop account. The dependency helper invokes
`sudo dnf install` itself. Do **not** run `build-appimage.sh` with `sudo`;
otherwise generated files become root-owned. Root-based CI containers can set
`ALLOW_ROOT_BUILD=1` explicitly.

The shared helper recognizes Fedora 43 and Fedora 44 and builds natively on x86_64 or aarch64. Compatibility wrappers
remain in `packaging/fedora43/` and `packaging/fedora44/`, but new builds should
use `python_lair2/packaging/fedora/`.

The static release check runs before generated build files are created. Local
`__pycache__` and `.pyc` files are treated as normal ignored working-tree
artifacts. They fail validation only if Git reports that they are tracked.

The build script creates a dedicated virtual environment, installs the runtime
and pinned build requirements, runs the release check, builds a PyInstaller
one-folder bundle, assembles an AppDir, validates desktop metadata when tools
are available, and produces an AppImage plus SHA-256 file.

Output:

```text
python_lair2/dist/Python-Lair-2.1.1-x86_64.AppImage
python_lair2/dist/Python-Lair-2.1.1-x86_64.AppImage.sha256
python_lair2/dist/Python-Lair-2.1.1-x86_64.AppImage.build-info.txt
python_lair2/dist/Python-Lair-2.1.1-x86_64.AppImage.build-python-lock.txt
```


## Recovering from an earlier sudo build

An earlier `sudo ./python_lair2/packaging/fedora/build-appimage.sh` may have left root-owned
generated directories. Remove them once, then rebuild as your normal user:

```bash
sudo rm -rf build dist-appimage
./python_lair2/packaging/fedora/build-appimage.sh
```

These directories contain generated artifacts only. Do not remove the project
source directory.

## Reproducibility notes

- Build from a clean checkout or release tag.
- Do not build from a general-purpose virtual environment.
- Keep the generated `.build-info.txt` beside the public artifact; it records
  the distribution, architecture, Python, PyQt6/Qt, and PyInstaller versions.
- Record the appimagetool version separately when publishing the release.
- The desktop environment must not be treated as an application dependency.
- Test the identical AppImage on XFCE, Plasma, and a Wayland environment when
  possible.
- A build made on a newer glibc baseline may not run on older distributions.
  A controlled conservative build environment is a future packaging goal.

## Override version or output

```bash
VERSION=2.1.1 OUTPUT_DIR="$PWD/release" \
  ./python_lair2/packaging/fedora/build-appimage.sh
```
