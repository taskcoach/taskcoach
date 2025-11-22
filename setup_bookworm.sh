#!/bin/bash
# TaskCoach Setup Script for Debian Bookworm
# This script automates the setup and testing of TaskCoach on Debian 12
# Updated to handle PEP 668 properly
#
# Version: 1.1.1.003 (f20c4dc)
# Branch: claude/add-module-loading-logs-01SvgNHroJJfg6fZCGp2mqd5
# Last Updated: 2025-11-16

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}TaskCoach Setup for Debian Bookworm${NC}"
echo -e "${BLUE}Version 1.1.1.003 (f20c4dc)${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if running on Debian
if [ ! -f /etc/debian_version ]; then
    echo -e "${YELLOW}Warning: This doesn't appear to be Debian${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Python version
echo -e "${BLUE}[1/7] Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo "Found Python $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
    echo -e "${GREEN}✓ Python version is compatible${NC}"
else
    echo -e "${RED}✗ Python 3.11+ required, found $PYTHON_VERSION${NC}"
    exit 1
fi
echo

# Install system dependencies
echo -e "${BLUE}[2/7] Installing system dependencies...${NC}"
echo "This will install system packages from Debian repos."
echo "Packages: python3-wxgtk4.0, python3-twisted, python3-lxml, python3-numpy,"
echo "          python3-six, python3-dateutil, python3-chardet, python3-keyring,"
echo "          python3-pyparsing, python3-pyxdg, python3-venv"
echo "Requires sudo privileges."

if command -v sudo &> /dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y \
        python3-wxgtk4.0 \
        python3-six \
        python3-twisted \
        python3-lxml \
        python3-numpy \
        python3-dateutil \
        python3-chardet \
        python3-keyring \
        python3-pyparsing \
        python3-pyxdg \
        python3-venv
    echo -e "${GREEN}✓ System packages installed${NC}"
else
    echo -e "${YELLOW}⚠ sudo not available, please install packages manually${NC}"
    exit 1
fi
echo

# Create virtual environment for packages not in Debian repos
echo -e "${BLUE}[3/7] Creating virtual environment...${NC}"
VENV_PATH="$SCRIPT_DIR/.venv"

if [ -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}Virtual environment already exists at $VENV_PATH${NC}"
    read -p "Recreate it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_PATH"
        python3 -m venv --system-site-packages "$VENV_PATH"
        echo -e "${GREEN}✓ Virtual environment recreated${NC}"
    else
        echo -e "${GREEN}✓ Using existing virtual environment${NC}"
    fi
else
    python3 -m venv --system-site-packages "$VENV_PATH"
    echo -e "${GREEN}✓ Virtual environment created in project directory${NC}"
fi
echo

# Install Python dependencies not available in Debian repos
echo -e "${BLUE}[4/7] Installing Python dependencies in venv...${NC}"
echo "Installing: desktop3, lockfile, gntp, distro, pypubsub, zeroconf, pyparsing>=3.1.3"

source "$VENV_PATH/bin/activate"
# Note: pyparsing>=3.1.3 required for deltaTime.py (Debian Bookworm only has 3.0.9)
pip install --quiet desktop3 lockfile gntp distro pypubsub zeroconf 'pyparsing>=3.1.3'
deactivate

echo -e "${GREEN}✓ Python dependencies installed in virtual environment${NC}"
echo

# Check launch script
echo -e "${BLUE}[5/7] Checking launch script...${NC}"
if [ -f "$SCRIPT_DIR/taskcoach-run.sh" ]; then
    chmod +x "$SCRIPT_DIR/taskcoach-run.sh"
    echo -e "${GREEN}✓ Launch script is ready: taskcoach-run.sh${NC}"
else
    echo -e "${RED}✗ Launch script not found${NC}"
    echo "taskcoach-run.sh should be included in the repository"
    exit 1
fi
echo

# Test installation
echo -e "${BLUE}Testing installation...${NC}"
echo "===================="
echo

# Test 1: Import taskcoachlib
echo -n "Testing taskcoachlib import... "
if VERSION=$(python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); import taskcoachlib.meta.data as meta; print(meta.version)" 2>/dev/null); then
    echo -e "${GREEN}✓ (version $VERSION)${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    exit 1
fi

# Test 2: Import wx
echo -n "Testing wxPython import... "
if WX_VERSION=$(python3 -c "import wx; print(wx.__version__)" 2>/dev/null); then
    echo -e "${GREEN}✓ (version $WX_VERSION)${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    echo "Please check python3-wxgtk4.0 installation"
    exit 1
fi

# Test 3: Test venv packages individually
echo "Testing virtual environment packages..."
source "$VENV_PATH/bin/activate"

VENV_FAILED=0

# desktop3 package provides 'desktop' module
echo -n "  - desktop3... "
if python3 -c "import desktop" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    VENV_FAILED=1
fi

# Test other packages
for pkg in "lockfile" "gntp" "distro" "zeroconf"; do
    echo -n "  - $pkg... "
    if python3 -c "import $pkg" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Failed${NC}"
        VENV_FAILED=1
    fi
done

# pypubsub package provides 'pubsub' module
echo -n "  - pypubsub... "
if python3 -c "from pubsub import pub" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    VENV_FAILED=1
fi

deactivate

if [ $VENV_FAILED -eq 1 ]; then
    echo -e "${RED}✗ Some packages failed to import${NC}"
    echo "Try recreating the virtual environment:"
    echo "  rm -rf $VENV_PATH"
    echo "  python3 -m venv --system-site-packages $VENV_PATH"
    echo "  source $VENV_PATH/bin/activate"
    echo "  pip install desktop3 lockfile gntp distro pypubsub"
    exit 1
fi

# Test 4: Run help
echo -n "Testing application help... "
if "$SCRIPT_DIR/taskcoach-run.sh" --help &>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    exit 1
fi

# Test 5: Quick GUI test (skip if no display)
if [ -n "$DISPLAY" ]; then
    echo -n "Testing GUI initialization... "
    if timeout 3 "$SCRIPT_DIR/taskcoach-run.sh" 2>&1 | grep -q "TaskCoach\|wx" || [ $? -eq 124 ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠ Could not fully test (this is OK)${NC}"
    fi
else
    echo "Skipping GUI test (no display available)"
fi

echo
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}[6/7] Applying wxPython patch...${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Apply the wxPython background color patch automatically
if [ -f "$SCRIPT_DIR/apply-wxpython-patch.sh" ]; then
    "$SCRIPT_DIR/apply-wxpython-patch.sh"
else
    echo -e "${YELLOW}⚠ Warning: apply-wxpython-patch.sh not found${NC}"
    echo "  Category row background coloring may not work correctly"
fi

echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo "TaskCoach has been set up with:"
echo "  • System packages from Debian repos (wxPython, numpy, lxml, etc.)"
echo "  • Virtual environment at: $SCRIPT_DIR/.venv"
echo "  • Additional packages in venv (desktop3, lockfile, gntp, distro, pypubsub, zeroconf)"
echo "  • wxPython background color patch (for category row coloring)"
echo
echo "You can now run TaskCoach with:"
echo -e "  ${BLUE}./taskcoach-run.sh${NC}"
echo
echo "To see all options:"
echo -e "  ${BLUE}./taskcoach-run.sh --help${NC}"
echo
echo "For more information, see DEBIAN_BOOKWORM_SETUP.md"
echo
