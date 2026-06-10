#!/bin/bash
#
# Build Task Coach as a Flatpak locally, alongside the AppImage build.
# Produces an installed app and a single-file .flatpak bundle that can be
# distributed directly (flatpak install ./TaskCoach-*.flatpak).
#
# Requires: flatpak, flatpak-builder, network access (first run pulls the
# GNOME runtime/SDK and the pinned Python sources).
#
# Usage: ./scripts/build-flatpak.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FLATPAK_DIR="$PROJECT_ROOT/build.in/flatpak"
MANIFEST="$FLATPAK_DIR/io.github.taskcoach.TaskCoach.yaml"
BUILD_DIR="$PROJECT_ROOT/build/flatpak"
APP_ID="io.github.taskcoach.TaskCoach"
RUNTIME_VERSION="50"

echo "=========================================="
echo "Task Coach Flatpak Builder"
echo "=========================================="

for cmd in flatpak flatpak-builder; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "Missing dependency: $cmd"
        echo "Install with: sudo apt install flatpak flatpak-builder"
        echo "  (or: sudo dnf install flatpak flatpak-builder)"
        exit 1
    fi
done

# Ensure the shared-modules submodule (libappindicator chain) is present.
git -C "$PROJECT_ROOT" submodule update --init build.in/flatpak/shared-modules

# Version from the single source of truth.
VERSION="$(python3 -c "from taskcoachlib.meta import data; print(data.version_full)")"
echo "Version: $VERSION"

# Ensure the GNOME runtime and SDK are present.
flatpak remote-add --user --if-not-exists flathub \
    https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user -y flathub \
    "org.gnome.Platform//$RUNTIME_VERSION" \
    "org.gnome.Sdk//$RUNTIME_VERSION"

# The manifest builds offline and includes pinned pip sources, so generate them
# first. This is the one step that needs the network; the build itself does not.
# Requires the GNOME Sdk installed just above (for --runtime ABI detection).
"$FLATPAK_DIR/generate-pip-sources.sh"

# Build, install for the current user, and export a repo.
rm -rf "$BUILD_DIR"
flatpak-builder --user --install --force-clean \
    --repo="$BUILD_DIR/repo" \
    "$BUILD_DIR/build" "$MANIFEST"

# Produce a single-file bundle that references Flathub for the runtime.
flatpak build-bundle \
    --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo \
    "$BUILD_DIR/repo" \
    "$PROJECT_ROOT/TaskCoach-${VERSION}-x86_64.flatpak" \
    "$APP_ID"

echo ""
echo "=========================================="
echo "Flatpak built successfully!"
echo "=========================================="
echo "Bundle: $PROJECT_ROOT/TaskCoach-${VERSION}-x86_64.flatpak"
echo ""
echo "Run the installed app:"
echo "  flatpak run $APP_ID"
echo ""
echo "Install the bundle elsewhere:"
echo "  flatpak install ./TaskCoach-${VERSION}-x86_64.flatpak"
echo ""
