#!/bin/bash
#
# Generate the pinned pip sources the Flatpak manifest includes.
#
# The manifest builds OFFLINE (the way Flathub builds), so it cannot let pip
# reach PyPI. This produces the two generated sub-manifests it includes:
#
#   * python3-sources.json            - the runtime Python deps
#   * python3-build-deps.json - wxPython's PEP 518 build backends
#
# wxPython itself is a separate pinned sdist that compiles its own bundled
# wxWidgets. CI and scripts/build-flatpak.sh run this before building. For a
# Flathub submission, run it and commit the two JSON files (Flathub does not
# generate at build time). See docs/FLATPAK.md.
#
# Requires flatpak + the GNOME Sdk installed (for --runtime ABI detection).
#
# Usage: build.in/flatpak/generate-pip-sources.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# pip/flatpak-pip-generator is a symlink upstream; raw.github serves the symlink
# target as text, so fetch the real .py file, not the bare name.
GENERATOR_URL="https://raw.githubusercontent.com/flatpak/flatpak-builder-tools/master/pip/flatpak-pip-generator.py"
OUT="$SCRIPT_DIR/python3-sources.json"

# Mirror the manifest's python3-deps set exactly so the offline build installs
# the same packages, all pure-Python. wxPython/wxWidgets are separate pinned
# source modules.
REQUIREMENTS=(
    "chardet>=5.2.0"
    "python-dateutil>=2.9.0"
    "squaremap>=1.0.5"
    "pyenchant>=3.2.0"
)

# Python build backends the OFFLINE build needs but pip cannot fetch from PyPI
# under --no-build-isolation. They are installed (as python3-build-deps.json)
# before any module that builds from an sdist:
#   - wxPython: setuptools/wheel/cython/sip/requests (its build-system.requires;
#     keep these in sync with wxpython-4.3.1).
BUILD_REQUIREMENTS=(
    "setuptools>=70.1"
    "wheel"
    "cython>=3.0.10"
    "requests>=2.26.0"
    "sip==6.12.0"
)

echo "Fetching flatpak-pip-generator..."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
wget -q "$GENERATOR_URL" -O "$TMP/flatpak-pip-generator"
python3 -m pip install --quiet --user requirements-parser packaging || true

# --runtime makes the generator read the TARGET Python's version/ABI tags from
# the GNOME Sdk (generating on the host would pin the wrong ABI).
# --ignore-installed lists packages pip must install into /app even when the
# build's org.gnome.Sdk already ships them: without it pip sees
# them "already satisfied", skips them, and they are MISSING at runtime against
# org.gnome.Platform, crashing the app with ModuleNotFoundError. We pass every
# runtime dep by name; names the Sdk does not ship are harmless no-ops. Requires
# flatpak + the Sdk: flatpak install -y flathub org.gnome.Sdk//$RUNTIME_VERSION
RUNTIME_VERSION="50"
# Package names only (strip version specifiers), comma-separated.
IGNORE_INSTALLED="$(printf '%s\n' "${REQUIREMENTS[@]}" | sed -E 's/[<>=!~,].*//' | paste -sd,)"
echo "Generating $OUT ..."
python3 "$TMP/flatpak-pip-generator" \
    --runtime "org.gnome.Sdk//$RUNTIME_VERSION" \
    --ignore-installed="$IGNORE_INSTALLED" \
    --output "$SCRIPT_DIR/python3-sources" \
    "${REQUIREMENTS[@]}"

echo "Wrote $OUT"

# Offline build backends -> python3-build-deps.json. --prefer-wheels for all so
# cython/sip resolve to the runtime's cp3xx wheels rather than compiling from
# sdist (the rest are pure-Python wheels anyway).
BUILD_OUT="$SCRIPT_DIR/python3-build-deps.json"
echo "Generating $BUILD_OUT ..."
python3 "$TMP/flatpak-pip-generator" \
    --runtime "org.gnome.Sdk//$RUNTIME_VERSION" \
    --prefer-wheels=setuptools,wheel,cython,requests,sip \
    --output "$SCRIPT_DIR/python3-build-deps" \
    "${BUILD_REQUIREMENTS[@]}"
echo "Wrote $BUILD_OUT"
echo "Review them, then build with build.in/flatpak or scripts/build-flatpak.sh"
