#!/bin/bash
# Build Debian package for Task Coach
# This script can be run locally or in CI to create .deb packages

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${PROJECT_DIR}/build-deb"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check if running on Debian/Ubuntu
check_system() {
    if [ ! -f /etc/debian_version ]; then
        error "This script must be run on Debian or Ubuntu"
    fi

    DISTRO=$(lsb_release -cs 2>/dev/null || cat /etc/debian_version | cut -d'/' -f1)
    info "Building on: $DISTRO"
}

# Install build dependencies
install_deps() {
    info "Installing build dependencies..."

    # Check if we have sudo
    if command -v sudo &> /dev/null; then
        SUDO="sudo"
    else
        SUDO=""
    fi

    $SUDO apt-get update
    $SUDO apt-get install -y \
        build-essential \
        debhelper \
        dh-python \
        python3-all \
        python3-setuptools \
        devscripts \
        lintian \
        fakeroot
}

# Clean previous build
clean_build() {
    info "Cleaning previous build artifacts..."
    rm -rf "$BUILD_DIR"
    rm -f "${PROJECT_DIR}"/../taskcoach_*.deb
    rm -f "${PROJECT_DIR}"/../taskcoach_*.changes
    rm -f "${PROJECT_DIR}"/../taskcoach_*.buildinfo
    rm -f "${PROJECT_DIR}"/../taskcoach_*.dsc
    rm -f "${PROJECT_DIR}"/../taskcoach_*.tar.*
}

# Get version from Python
get_version() {
    cd "$PROJECT_DIR"
    VERSION=$(python3 -c "
import sys
sys.path.insert(0, '.')
from taskcoachlib.meta import data
print(data.version_full)
")
    echo "$VERSION"
}

# Build the package
build_package() {
    cd "$PROJECT_DIR"

    info "Building Debian package..."
    VERSION=$(get_version)
    info "Package version: $VERSION"

    # Build source package
    info "Building source package..."
    dpkg-buildpackage -us -uc -S

    # Build binary package
    info "Building binary package..."
    dpkg-buildpackage -us -uc -b

    info "Build complete!"
    info "Packages are in the parent directory:"
    ls -la ../*.deb 2>/dev/null || warn "No .deb files found"
    ls -la ../*.changes 2>/dev/null || true
}

# Run lintian checks
run_lintian() {
    cd "$PROJECT_DIR"

    info "Running lintian checks..."

    CHANGES_FILE=$(ls ../*.changes 2>/dev/null | head -1)
    if [ -n "$CHANGES_FILE" ]; then
        info "Checking $CHANGES_FILE"
        lintian --info --display-info "$CHANGES_FILE" || true
    fi

    DEB_FILE=$(ls ../*.deb 2>/dev/null | head -1)
    if [ -n "$DEB_FILE" ]; then
        info "Checking $DEB_FILE"
        lintian --info --display-info "$DEB_FILE" || true
    fi
}

# Test installation
test_install() {
    cd "$PROJECT_DIR"

    DEB_FILE=$(ls ../*.deb 2>/dev/null | head -1)
    if [ -z "$DEB_FILE" ]; then
        error "No .deb file found to test"
    fi

    info "Testing installation of $DEB_FILE..."

    # Check if we have sudo
    if command -v sudo &> /dev/null; then
        SUDO="sudo"
    else
        SUDO=""
    fi

    # Try to install (may fail on dependencies)
    $SUDO dpkg -i "$DEB_FILE" || {
        warn "Installation failed, attempting to fix dependencies..."
        $SUDO apt-get install -f -y
    }

    # Verify installation
    dpkg -l | grep taskcoach || error "Package not installed"

    # Test Python import
    python3 -c "import taskcoachlib; print('taskcoachlib imported from:', taskcoachlib.__file__)" || \
        error "Failed to import taskcoachlib"

    info "Installation test passed!"
}

# Show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS] [COMMAND]

Build Debian packages for Task Coach.

Commands:
    build       Build the .deb package (default)
    clean       Clean build artifacts
    deps        Install build dependencies
    lintian     Run lintian checks on built package
    test        Test installing the built package
    all         Run all steps: clean, deps, build, lintian

Options:
    -h, --help  Show this help message

Examples:
    $0              # Build the package
    $0 all          # Full build with dependency installation
    $0 lintian      # Run lintian on existing package
    $0 test         # Test installing the package

EOF
}

# Main
main() {
    case "${1:-build}" in
        build)
            check_system
            build_package
            ;;
        clean)
            clean_build
            ;;
        deps)
            check_system
            install_deps
            ;;
        lintian)
            run_lintian
            ;;
        test)
            check_system
            test_install
            ;;
        all)
            check_system
            clean_build
            install_deps
            build_package
            run_lintian
            ;;
        -h|--help)
            usage
            ;;
        *)
            error "Unknown command: $1"
            ;;
    esac
}

main "$@"
