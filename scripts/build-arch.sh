#!/bin/bash
# TaskCoach Arch/Manjaro Package Build Script
# Builds a .pkg.tar.zst package for installation on Arch/Manjaro Linux
#
# Usage:
#   ./scripts/build-arch.sh           # Build package from current source
#   ./scripts/build-arch.sh --install # Build and install package
#
# Requirements:
#   - base-devel package group installed
#   - makepkg command available
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build-area/arch"
INSTALL_PKG=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --install|-i)
            INSTALL_PKG=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --install, -i    Install the package after building"
            echo "  --help, -h       Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}TaskCoach Arch/Manjaro Package Builder${NC}"
echo -e "${BLUE}Version 1.0.0${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if we're on an Arch-based system
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "manjaro" ] && [ "$ID" != "arch" ] && [ "$ID_LIKE" != "arch" ]; then
        echo -e "${YELLOW}Warning: This script is designed for Arch/Manjaro Linux${NC}"
        echo -e "${YELLOW}Detected: $PRETTY_NAME${NC}"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Check for required tools
echo -e "${BLUE}[1/5] Checking build requirements...${NC}"

if ! command -v makepkg &> /dev/null; then
    echo -e "${RED}✗ makepkg not found${NC}"
    echo "Please install the base-devel package group:"
    echo "  sudo pacman -S base-devel"
    exit 1
fi
echo -e "${GREEN}✓ makepkg found${NC}"

# Get version from meta data
echo -e "${BLUE}[2/5] Getting version information...${NC}"
cd "$PROJECT_ROOT"

VERSION=$(python3 -c "import sys; sys.path.insert(0, '.'); from taskcoachlib.meta import data; print(data.version)")
PATCH=$(python3 -c "import sys; sys.path.insert(0, '.'); from taskcoachlib.meta import data; print(data.version_patch)")
FULL_VERSION="${VERSION}.${PATCH}"

echo "Version: $FULL_VERSION"
echo -e "${GREEN}✓ Version detected${NC}"
echo

# Create build directory
echo -e "${BLUE}[3/5] Setting up build directory...${NC}"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy source to build directory
echo "Copying source files..."
tar --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='build-area' \
    --exclude='.mypy_cache' \
    --exclude='.pytest_cache' \
    --exclude='*.egg-info' \
    -czf "$BUILD_DIR/taskcoach-$FULL_VERSION.tar.gz" \
    -C "$PROJECT_ROOT/.." \
    "$(basename "$PROJECT_ROOT")"

# Rename directory in tarball for consistency
cd "$BUILD_DIR"
mkdir tmp
cd tmp
tar -xzf ../taskcoach-$FULL_VERSION.tar.gz
mv "$(ls)" "taskcoach-$FULL_VERSION"
tar -czf ../taskcoach-$FULL_VERSION.tar.gz "taskcoach-$FULL_VERSION"
cd ..
rm -rf tmp

# Generate sha256sum
SHA256=$(sha256sum "taskcoach-$FULL_VERSION.tar.gz" | cut -d' ' -f1)
echo "SHA256: $SHA256"

# Copy and update PKGBUILD
cp "$PROJECT_ROOT/build.in/arch/PKGBUILD" "$BUILD_DIR/"
cp "$PROJECT_ROOT/build.in/arch/taskcoach.install" "$BUILD_DIR/"

# Update PKGBUILD with correct version and checksum
sed -i "s/^pkgver=.*/pkgver=$FULL_VERSION/" "$BUILD_DIR/PKGBUILD"
sed -i "s/^sha256sums=.*/sha256sums=('$SHA256')/" "$BUILD_DIR/PKGBUILD"

# Update source to use local tarball
sed -i "s|^source=.*|source=(\"taskcoach-\$pkgver.tar.gz\")|" "$BUILD_DIR/PKGBUILD"

# Simplify prepare() for local build
cat > "$BUILD_DIR/PKGBUILD.local" << 'PKGBUILD_EOF'
# Maintainer: Task Coach developers <developers@taskcoach.org>
# Contributor: Aaron Wolf <https://github.com/realcarbonneau>
# Local build from source

PKGBUILD_EOF

# Append the rest of PKGBUILD but modify prepare()
sed -n '/^pkgname=/,$p' "$BUILD_DIR/PKGBUILD" | \
    sed 's/prepare() {/prepare() {\n    # Local build - directory is already named correctly\n    true\n    return\n    # Original prepare code below (not executed):/' \
    >> "$BUILD_DIR/PKGBUILD.local"

mv "$BUILD_DIR/PKGBUILD.local" "$BUILD_DIR/PKGBUILD"

echo -e "${GREEN}✓ Build directory ready${NC}"
echo

# Build package
echo -e "${BLUE}[4/5] Building package...${NC}"
cd "$BUILD_DIR"

# Run makepkg (skip checksums for local build, we just generated them)
makepkg -sf --noconfirm

PKG_FILE=$(ls taskcoach-*.pkg.tar.* 2>/dev/null | head -1)

if [ -z "$PKG_FILE" ]; then
    echo -e "${RED}✗ Package build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Package built: $PKG_FILE${NC}"
echo

# Copy package to project root build-area
cp "$PKG_FILE" "$PROJECT_ROOT/build-area/"
echo "Package copied to: $PROJECT_ROOT/build-area/$PKG_FILE"
echo

# Install if requested
if [ "$INSTALL_PKG" = true ]; then
    echo -e "${BLUE}[5/5] Installing package...${NC}"
    sudo pacman -U --noconfirm "$BUILD_DIR/$PKG_FILE"
    echo -e "${GREEN}✓ Package installed${NC}"
else
    echo -e "${BLUE}[5/5] Skipping installation (use --install to install)${NC}"
fi

echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Build completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo "Package location: $PROJECT_ROOT/build-area/$PKG_FILE"
echo
echo "To install the package:"
echo -e "  ${BLUE}sudo pacman -U $PROJECT_ROOT/build-area/$PKG_FILE${NC}"
echo
echo "To uninstall:"
echo -e "  ${BLUE}sudo pacman -R taskcoach${NC}"
echo
