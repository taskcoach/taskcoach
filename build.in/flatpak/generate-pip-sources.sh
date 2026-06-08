#!/bin/bash
#
# Generate python3-sources.json for the Flatpak manifest.
#
# This is ONLY needed for an offline Flathub submission. The default manifest
# (and our own CI/local builds) fetch deps over the network with --share=network
# and do not need this file.
#
# wxPython is already offline-ready in the manifest: it is a pinned sdist that
# builds its own bundled wxWidgets. So this generator only needs to cover the
# remaining PURE-PYTHON deps (the python3-deps module). Run it, commit
# python3-sources.json, switch the manifest to include it instead of the network
# python3-deps module, and drop --share=network. See docs/FLATPAK.md.
#
# Usage: build.in/flatpak/generate-pip-sources.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GENERATOR_URL="https://raw.githubusercontent.com/flatpak/flatpak-builder-tools/master/pip/flatpak-pip-generator"
OUT="$SCRIPT_DIR/python3-sources.json"

# Pure-Python deps only (wxPython/wxWidgets are pinned source modules already).
REQUIREMENTS=(
    "six>=1.16.0"
    "pypubsub"
    "watchdog>=3.0.0"
    "chardet>=5.2.0"
    "python-dateutil>=2.9.0"
    "pyparsing>=3.1.3"
    "lxml"
    "pyxdg"
    "keyring"
    "numpy>=1.26,<2"
    "fasteners>=0.19"
    "squaremap>=1.0.5"
    "pyenchant>=3.2.0"
    "distro"
)

echo "Fetching flatpak-pip-generator..."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
wget -q "$GENERATOR_URL" -O "$TMP/flatpak-pip-generator"
python3 -m pip install --quiet --user requirements-parser || true

echo "Generating $OUT ..."
python3 "$TMP/flatpak-pip-generator" \
    --output "$SCRIPT_DIR/python3-sources" \
    "${REQUIREMENTS[@]}"

# flatpak-pip-generator writes python3-sources.json next to --output.
echo "Wrote $OUT"
echo "Review it, then build with build.in/flatpak or scripts/build-flatpak.sh"
