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
# the same packages. Most are pure-Python; dbus-python is a C extension (idle
# detection) built from its pinned sdist in the runtime, whose Sdk ships the
# dbus/glib dev headers. wxPython/wxWidgets are separate pinned source modules.
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
    # numpy: the other builds pin <2 (numpy 1.26.4, the final 1.x), but that
    # release only ships wheels for Python 3.9-3.12 and the GNOME runtime is
    # Python 3.13, so <2 is unsatisfiable here. The real constraint behind that
    # pin is avoiding numpy 2.4+, which raised its CPU baseline to SSE4.2 and
    # crashes older CPUs with ILLEGAL INSTRUCTION (see docs/NUMPY.md). numpy
    # 2.1-2.3 have cp313 wheels and keep the old baseline, and Task Coach's use
    # (uint8 array ops) is numpy-2.x-safe, so pin <2.4 for the flatpak.
    "numpy>=1.26,<2.4"
    "fasteners>=0.19"
    "squaremap>=1.0.5"
    "pyenchant>=3.2.0"
    "dbus-python>=1.3.2"
    "distro"
)

# Python build backends the OFFLINE build needs but pip cannot fetch from PyPI
# under --no-build-isolation. They are installed (as python3-build-deps.json)
# before any module that builds from an sdist:
#   - wxPython: setuptools/wheel/cython/sip/requests (its build-system.requires;
#     keep these in sync with wxpython-4.2.5).
#   - dbus-python 1.4.x: meson-python (it builds with meson; meson and ninja
#     themselves come from the Sdk, only the Python backend is missing), plus
#     patchelf, which meson-python shells out to for fixing the built C
#     extension's rpath and which the Sdk does not ship. The patchelf PyPI
#     wheel bundles the binary; pip installs it to /app/bin (on PATH at build).
BUILD_REQUIREMENTS=(
    "setuptools>=70.1"
    "wheel"
    "cython>=3.0.10"
    "requests>=2.26.0"
    "sip==6.12.0"
    "meson-python"
    "patchelf"
)

echo "Fetching flatpak-pip-generator..."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
wget -q "$GENERATOR_URL" -O "$TMP/flatpak-pip-generator"
python3 -m pip install --quiet --user requirements-parser packaging || true

# --runtime makes the generator read the TARGET Python's version/ABI tags from
# the GNOME Sdk, so numpy/lxml/cryptography resolve to the correct cp3xx
# manylinux wheels (generating on the host would pin the wrong ABI).
# --prefer-wheels avoids compiling those heavy binary deps from sdist;
# dbus-python is intentionally left off it (no wheels exist) and builds from its
# sdist against the Sdk's dbus/glib headers.
# --ignore-installed lists packages pip must install into /app even when the
# build's org.gnome.Sdk already ships them (notably lxml): without it pip sees
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
    --prefer-wheels=numpy,lxml,cryptography,cffi \
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
    --prefer-wheels=setuptools,wheel,cython,requests,sip,meson-python,patchelf \
    --output "$SCRIPT_DIR/python3-build-deps" \
    "${BUILD_REQUIREMENTS[@]}"
echo "Wrote $BUILD_OUT"
echo "Review them, then build with build.in/flatpak or scripts/build-flatpak.sh"
