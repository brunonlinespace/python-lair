#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 /path/to/Python-Lair-2.1.1-<arch>.AppImage" >&2
    exit 2
fi

IMAGE="$(readlink -f "$1")"
if [[ ! -f "$IMAGE" ]]; then
    echo "AppImage not found: $IMAGE" >&2
    exit 2
fi

chmod +x "$IMAGE"
echo "File information:"
file "$IMAGE"
echo
echo "Version check without requiring FUSE:"
"$IMAGE" --appimage-extract-and-run --version

echo
echo "Starting graphical smoke test. Close Python Lair 2 to finish."
"$IMAGE" --appimage-extract-and-run
