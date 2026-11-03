# Python Lair Packaging

## Fedora 43/44 native x86_64/aarch64 AppImage

```bash
./python_lair2/packaging/fedora/install-build-deps.sh
./python_lair2/packaging/fedora/build-appimage.sh
```

Run the build as your normal user. The dependency installer uses `sudo`
internally; do not invoke `build-appimage.sh` with `sudo`.

Expected artifacts:

```text
python_lair2/dist/Python-Lair-2.1.1-x86_64.AppImage
python_lair2/dist/Python-Lair-2.1.1-x86_64.AppImage.sha256
python_lair2/dist/Python-Lair-2.1.1-x86_64.AppImage.build-info.txt
python_lair2/dist/Python-Lair-2.1.1-x86_64.AppImage.build-python-lock.txt
```

Test an artifact with:

```bash
./python_lair2/packaging/fedora/test-appimage.sh   python_lair2/dist/Python-Lair-2.1.1-x86_64.AppImage
```

The build uses a clean virtual environment and pinned PyInstaller and
PyInstaller-hooks versions from `packaging/pyinstaller/build-requirements.txt`. Runtime PyQt6 constraints are
in `python_lair2/requirements.txt`.

Read `BUILDING.md` before creating a public release. Build-host desktop
integration must not be allowed to become an undeclared application dependency.

The shared Fedora scripts recognize releases 43 and 44. The `fedora43` and
`fedora44` directories contain compatibility wrappers only.

The source release check runs before creation of the build virtual environment.
Generated build areas and ordinary local Python caches are excluded from
working-tree hygiene failures. Cache files still fail validation if they are
actually tracked by Git.
