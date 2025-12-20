#!/bin/bash
#
# Build TaskCoach AppImage locally
# This script can be run on Debian Bookworm or similar systems
#
# Usage: ./scripts/build-appimage.sh
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_ROOT/build/appimage"
APPDIR="$BUILD_DIR/TaskCoach.AppDir"

echo "=========================================="
echo "TaskCoach AppImage Builder"
echo "=========================================="
echo "Project root: $PROJECT_ROOT"
echo "Build directory: $BUILD_DIR"
echo ""

# Check for required tools
check_dependencies() {
    local missing=""

    for cmd in wget file patchelf; do
        if ! command -v $cmd &> /dev/null; then
            missing="$missing $cmd"
        fi
    done

    if [ -n "$missing" ]; then
        echo "Missing dependencies:$missing"
        echo ""
        echo "Install them with:"
        echo "  sudo apt-get install wget file patchelf"
        exit 1
    fi

    # Check for FUSE (needed to extract AppImage)
    if [ ! -f /usr/lib/x86_64-linux-gnu/libfuse.so.2 ] && [ ! -f /usr/lib/libfuse.so.2 ]; then
        echo "Note: libfuse2 not found. Will use --appimage-extract method."
    fi
}

# Clean previous build
clean_build() {
    echo "Cleaning previous build..."
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"
}

# Download Python AppImage base
download_python_appimage() {
    echo "Downloading Python 3.11 AppImage base..."

    # Python 3.11 with manylinux_2_28 (glibc 2.28+, compatible with Debian Bookworm)
    local url="https://github.com/niess/python-appimage/releases/download/python3.11/python3.11.14-cp311-cp311-manylinux_2_28_x86_64.AppImage"

    wget -q --show-progress "$url" -O "$BUILD_DIR/python.AppImage"
    chmod +x "$BUILD_DIR/python.AppImage"
}

# Extract Python AppImage
extract_python_appimage() {
    echo "Extracting Python AppImage..."
    cd "$BUILD_DIR"

    ./python.AppImage --appimage-extract
    mv squashfs-root "$APPDIR"

    cd "$PROJECT_ROOT"
}

# Install dependencies
install_dependencies() {
    echo "Installing wxPython and dependencies..."
    echo "This may take several minutes..."

    cd "$APPDIR"

    # The python-appimage bundles Python with correct paths
    # DO NOT set PYTHONHOME - it breaks the bundled Python's path resolution
    # Use the AppRun wrapper which sets up the environment correctly
    PYTHON="$(pwd)/AppRun"

    # Upgrade pip
    $PYTHON -m pip install --upgrade pip setuptools wheel

    # Install wxPython - use pre-built wheels from wxPython extras repository
    echo "Installing wxPython..."
    $PYTHON -m pip install -U -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-22.04 wxPython || \
        $PYTHON -m pip install wxPython --prefer-binary

    # Install TaskCoach dependencies
    echo "Installing TaskCoach dependencies..."
    $PYTHON -m pip install \
        "six>=1.16.0" \
        desktop3 \
        pypubsub \
        "watchdog>=3.0.0" \
        "chardet>=5.2.0" \
        "python-dateutil>=2.9.0" \
        "pyparsing>=3.1.3" \
        lxml \
        pyxdg \
        keyring \
        numpy \
        "fasteners>=0.19" \
        "gntp>=1.0.3" \
        "zeroconf>=0.50.0" \
        "squaremap>=1.0.5" \
        distro

    cd "$PROJECT_ROOT"
}

# Clean up unnecessary files
cleanup_appdir() {
    echo "Cleaning up to reduce AppImage size..."

    cd "$APPDIR"

    # Remove pip, setuptools, wheel (not needed at runtime)
    rm -rf ./usr/lib/python*/site-packages/pip
    rm -rf ./usr/lib/python*/site-packages/setuptools
    rm -rf ./usr/lib/python*/site-packages/wheel
    rm -rf ./usr/lib/python*/site-packages/pip-*
    rm -rf ./usr/lib/python*/site-packages/setuptools-*
    rm -rf ./usr/lib/python*/site-packages/wheel-*

    # Remove Python cache files
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true

    # Remove test directories (save space)
    find . -path "*/site-packages/*/tests" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -path "*/site-packages/*/test" -type d -exec rm -rf {} + 2>/dev/null || true

    cd "$PROJECT_ROOT"
}

# Copy TaskCoach application
copy_application() {
    echo "Copying TaskCoach application..."

    # Create application directory
    mkdir -p "$APPDIR/usr/share/taskcoach"

    # Copy TaskCoach source
    cp -r "$PROJECT_ROOT/taskcoachlib" "$APPDIR/usr/share/taskcoach/"
    cp "$PROJECT_ROOT/taskcoach.py" "$APPDIR/usr/share/taskcoach/"

    # Copy icons
    mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "$APPDIR/usr/share/pixmaps"

    if [ -f "$PROJECT_ROOT/icons.in/taskcoach.png" ]; then
        cp "$PROJECT_ROOT/icons.in/taskcoach.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/"
        cp "$PROJECT_ROOT/icons.in/taskcoach.png" "$APPDIR/usr/share/pixmaps/"
        cp "$PROJECT_ROOT/icons.in/taskcoach.png" "$APPDIR/taskcoach.png"
    fi
}

# Create AppRun script
create_apprun() {
    echo "Creating AppRun script..."

    cat > "$APPDIR/AppRun" << 'APPRUN_EOF'
#!/bin/bash

# AppRun script for Task Coach AppImage
# This script sets up the environment and launches the application

# Get the directory where this AppImage is mounted
APPDIR="$(dirname "$(readlink -f "$0")")"

# In python-appimage (manylinux), the actual Python binary is in opt/
# usr/bin/python3 is a wrapper script that breaks when PYTHONHOME is set
PYTHON="$APPDIR/opt/python3.11/bin/python3.11"

# Set up Python environment
export PYTHONHOME="$APPDIR/opt/python3.11"
export PYTHONPATH="$APPDIR/usr/share/taskcoach:$APPDIR/opt/python3.11/lib/python3.11/site-packages:$PYTHONPATH"

# Set up library paths
export LD_LIBRARY_PATH="$APPDIR/opt/python3.11/lib:$APPDIR/usr/lib:$LD_LIBRARY_PATH"

# Set up PATH
export PATH="$APPDIR/opt/python3.11/bin:$APPDIR/usr/bin:$PATH"

# Set up XDG paths for proper desktop integration
export XDG_DATA_DIRS="$APPDIR/usr/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"

# GTK settings for better compatibility
export GTK_THEME="${GTK_THEME:-Adwaita}"

# Disable Python bytecode generation in AppImage (read-only)
export PYTHONDONTWRITEBYTECODE=1

# Set application icon for window managers
export TASKCOACH_APPIMAGE=1

# Handle file associations - pass file arguments to TaskCoach
exec "$PYTHON" "$APPDIR/usr/share/taskcoach/taskcoach.py" "$@"
APPRUN_EOF

    chmod +x "$APPDIR/AppRun"
}

# Create desktop file
create_desktop_file() {
    echo "Creating desktop file..."

    cat > "$APPDIR/taskcoach.desktop" << 'DESKTOP_EOF'
[Desktop Entry]
Name=Task Coach
GenericName=Task Manager
Comment=Your friendly task manager
Exec=taskcoach %f
Icon=taskcoach
Terminal=false
Type=Application
Categories=Office;Calendar;ProjectManagement;
Keywords=task;todo;reminder;project;gtd;
MimeType=application/x-taskcoach;
StartupNotify=true
StartupWMClass=TaskCoach
DESKTOP_EOF

    mkdir -p "$APPDIR/usr/share/applications"
    cp "$APPDIR/taskcoach.desktop" "$APPDIR/usr/share/applications/"
}

# Create AppStream metadata
create_appdata() {
    echo "Creating AppStream metadata..."

    mkdir -p "$APPDIR/usr/share/metainfo"
    cat > "$APPDIR/usr/share/metainfo/taskcoach.appdata.xml" << 'APPDATA_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>org.taskcoach.TaskCoach</id>
  <name>Task Coach</name>
  <summary>Your friendly task manager</summary>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0+</project_license>
  <description>
    <p>
      Task Coach is a free open source todo manager. It grew out of
      frustration about other programs not handling composite tasks well.
    </p>
    <p>
      In addition to flexible composite tasks, Task Coach has grown to include
      prerequisites, prioritizing, effort tracking, category tags, budgets,
      notes, and many other features.
    </p>
    <p>
      However, users are not forced to use all these features; Task Coach can
      be as simple or complex as you need it to be.
    </p>
  </description>
  <launchable type="desktop-id">taskcoach.desktop</launchable>
  <url type="homepage">https://github.com/realcarbonneau/taskcoach</url>
  <url type="bugtracker">https://github.com/realcarbonneau/taskcoach/issues</url>
  <provides>
    <binary>taskcoach</binary>
  </provides>
  <content_rating type="oars-1.1" />
</component>
APPDATA_EOF
}

# Download appimagetool
download_appimagetool() {
    if [ ! -f "$BUILD_DIR/appimagetool" ]; then
        echo "Downloading appimagetool..."
        wget -q --show-progress \
            "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" \
            -O "$BUILD_DIR/appimagetool"
        chmod +x "$BUILD_DIR/appimagetool"
    fi
}

# Build the AppImage
build_appimage() {
    echo "Building AppImage..."

    cd "$BUILD_DIR"

    # Get version from TaskCoach
    VERSION=$(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
from taskcoachlib.meta import data
print(data.version_full)
" 2>/dev/null || echo "1.6.1")

    echo "Version: $VERSION"

    # Build AppImage
    ARCH=x86_64 ./appimagetool "$APPDIR" "TaskCoach-${VERSION}-x86_64.AppImage"

    # Move to project root
    mv "TaskCoach-${VERSION}-x86_64.AppImage" "$PROJECT_ROOT/"

    cd "$PROJECT_ROOT"

    echo ""
    echo "=========================================="
    echo "AppImage built successfully!"
    echo "=========================================="
    echo "Output: $PROJECT_ROOT/TaskCoach-${VERSION}-x86_64.AppImage"
    echo ""
    echo "To run:"
    echo "  ./TaskCoach-${VERSION}-x86_64.AppImage"
    echo ""
}

# Main execution
main() {
    check_dependencies
    clean_build
    download_python_appimage
    extract_python_appimage
    install_dependencies
    cleanup_appdir
    copy_application
    create_apprun
    create_desktop_file
    create_appdata
    download_appimagetool
    build_appimage
}

main "$@"
