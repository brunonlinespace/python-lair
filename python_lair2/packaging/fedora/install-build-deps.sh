#!/usr/bin/env bash
set -euo pipefail

if [[ ! -r /etc/os-release ]]; then
    echo "Cannot identify the operating system." >&2
    exit 1
fi

# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != "fedora" ]]; then
    echo "Warning: this helper is intended for Fedora; detected ${PRETTY_NAME:-unknown}." >&2
else
    case "${VERSION_ID:-}" in
        43|44)
            echo "Installing Python Lair AppImage build dependencies for Fedora ${VERSION_ID}."
            ;;
        *)
            echo "Warning: validated for Fedora 43 and 44; detected ${PRETTY_NAME:-unknown}." >&2
            ;;
    esac
fi

sudo dnf install -y \
    python3 \
    python3-pip \
    python3-devel \
    gcc \
    gcc-c++ \
    make \
    curl \
    file \
    desktop-file-utils \
    appstream \
    libxkbcommon-x11 \
    xcb-util-cursor \
    mesa-libGL \
    fontconfig \
    freetype

cat <<'EOF'
Fedora build dependencies installed.

FUSE is not required to build because the build script can run appimagetool
with extraction fallback. To run AppImages by mounting them instead of using
--appimage-extract-and-run, install the host FUSE package when available:

    sudo dnf install fuse
EOF
