#!/bin/bash
# TaskCoach Setup Script for Arch/Manjaro Linux
# This script automates the setup and testing of TaskCoach on Arch/Manjaro
#

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
echo -e "${BLUE}TaskCoach Setup for Arch/Manjaro Linux${NC}"
echo -e "${BLUE}Version 1.0.0${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check if running on Manjaro or Arch
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
else
    echo -e "${YELLOW}Warning: Cannot detect distribution${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Python version
echo -e "${BLUE}[1/8] Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo "Found Python $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
    echo -e "${GREEN}✓ Python version is compatible${NC}"
else
    echo -e "${RED}✗ Python 3.10+ required, found $PYTHON_VERSION${NC}"
    exit 1
fi
echo

# Install system dependencies
echo -e "${BLUE}[2/8] Installing system dependencies...${NC}"
echo "This will install system packages from Arch/Manjaro repos."
echo "Requires sudo privileges."

if command -v sudo &> /dev/null; then
    # Update package database
    sudo pacman -Sy --noconfirm

    # Install core dependencies from official repos
    sudo pacman -S --needed --noconfirm \
        python \
        python-wxpython \
        python-six \
        python-lxml \
        python-numpy \
        python-dateutil \
        python-chardet \
        python-keyring \
        python-pyparsing \
        python-pyxdg \
        python-watchdog \
        python-fasteners \
        python-zeroconf \
        libxss \
        xdg-utils

    echo -e "${GREEN}✓ System packages installed${NC}"
else
    echo -e "${YELLOW}⚠ sudo not available, please install packages manually${NC}"
    exit 1
fi
echo

# Check for AUR packages
echo -e "${BLUE}[3/8] Checking AUR packages...${NC}"
AUR_PACKAGES=""

# Check for python-pypubsub
if ! pacman -Q python-pypubsub &>/dev/null; then
    AUR_PACKAGES="$AUR_PACKAGES python-pypubsub"
fi

# Check for python-squaremap (optional)
if ! pacman -Q python-squaremap &>/dev/null; then
    echo -e "${YELLOW}Note: python-squaremap is optional (for hierarchical visualization)${NC}"
fi

# Check for python-gntp (optional)
if ! pacman -Q python-gntp &>/dev/null; then
    echo -e "${YELLOW}Note: python-gntp is optional (for Growl notifications)${NC}"
fi

if [ -n "$AUR_PACKAGES" ]; then
    echo -e "${YELLOW}The following packages need to be installed from AUR:${NC}"
    echo "  $AUR_PACKAGES"
    echo

    # Check for yay or paru
    if command -v yay &> /dev/null; then
        echo "Installing with yay..."
        yay -S --needed --noconfirm $AUR_PACKAGES
    elif command -v paru &> /dev/null; then
        echo "Installing with paru..."
        paru -S --needed --noconfirm $AUR_PACKAGES
    else
        echo -e "${YELLOW}No AUR helper found. Please install the following manually:${NC}"
        echo "  $AUR_PACKAGES"
        echo
        echo "You can install an AUR helper with:"
        echo "  sudo pacman -S yay  # or paru"
        echo "Then run: yay -S $AUR_PACKAGES"
    fi
else
    echo -e "${GREEN}✓ All AUR packages already installed${NC}"
fi
echo

# Create virtual environment
echo -e "${BLUE}[4/8] Creating virtual environment...${NC}"
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

# Install Python dependencies not available in Arch repos
echo -e "${BLUE}[5/8] Installing Python dependencies in venv...${NC}"
# Most packages are available in Arch repos, only install what's missing
echo "Installing: desktop3, distro"

source "$VENV_PATH/bin/activate"
pip install --quiet desktop3 distro

# Install optional packages if not available from system
if ! python3 -c "from pubsub import pub" 2>/dev/null; then
    echo "Installing pypubsub from pip..."
    pip install --quiet pypubsub
fi

if ! python3 -c "import squaremap" 2>/dev/null; then
    echo "Installing squaremap from pip (optional)..."
    pip install --quiet squaremap || echo -e "${YELLOW}squaremap install failed (optional)${NC}"
fi

if ! python3 -c "import gntp" 2>/dev/null; then
    echo "Installing gntp from pip (optional)..."
    pip install --quiet gntp || echo -e "${YELLOW}gntp install failed (optional)${NC}"
fi

deactivate

echo -e "${GREEN}✓ Python dependencies installed in virtual environment${NC}"
echo

# Check launch script
echo -e "${BLUE}[6/8] Checking launch script...${NC}"
if [ -f "$SCRIPT_DIR/taskcoach-run.sh" ]; then
    chmod +x "$SCRIPT_DIR/taskcoach-run.sh"
    echo -e "${GREEN}✓ Launch script is ready: taskcoach-run.sh${NC}"
else
    echo -e "${RED}✗ Launch script not found${NC}"
    echo "taskcoach-run.sh should be included in the repository"
    exit 1
fi
echo

# Apply wxPython patch
echo -e "${BLUE}[7/8] Applying wxPython patch...${NC}"
if [ -f "$SCRIPT_DIR/apply-wxpython-patch.sh" ]; then
    "$SCRIPT_DIR/apply-wxpython-patch.sh"
else
    echo -e "${YELLOW}⚠ Warning: apply-wxpython-patch.sh not found${NC}"
    echo "  Category row background coloring may not work correctly"
fi
echo

# Test installation
echo -e "${BLUE}[8/8] Testing installation...${NC}"
echo "===================="
echo

source "$VENV_PATH/bin/activate"

# Test 1: Import taskcoachlib
echo -n "Testing taskcoachlib import... "
if VERSION=$(python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); import taskcoachlib.meta.data as meta; print(meta.version)" 2>/dev/null); then
    echo -e "${GREEN}✓ (version $VERSION)${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    deactivate
    exit 1
fi

# Test 2: Import wx
echo -n "Testing wxPython import... "
if WX_VERSION=$(python3 -c "import wx; print(wx.__version__)" 2>/dev/null); then
    echo -e "${GREEN}✓ (version $WX_VERSION)${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    echo "Please check python-wxpython installation"
    deactivate
    exit 1
fi

# Test 3: Test key packages
echo "Testing key packages..."
FAILED=0

for pkg in "fasteners" "desktop" "distro" "zeroconf" "watchdog"; do
    echo -n "  - $pkg... "
    if python3 -c "import $pkg" 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Failed${NC}"
        FAILED=1
    fi
done

# pypubsub package provides 'pubsub' module
echo -n "  - pypubsub... "
if python3 -c "from pubsub import pub" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    FAILED=1
fi

deactivate

if [ $FAILED -eq 1 ]; then
    echo -e "${RED}✗ Some packages failed to import${NC}"
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

echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo "TaskCoach has been set up for Arch/Manjaro Linux with:"
echo "  • System packages from official repos (wxPython, numpy, lxml, fasteners, watchdog, etc.)"
echo "  • Virtual environment at: $SCRIPT_DIR/.venv"
echo "  • Additional packages in venv (desktop3, distro)"
echo "  • wxPython background color patch (for category row coloring)"
echo
echo "Optional packages (install from AUR if needed):"
echo "  • python-squaremap: Hierarchical data visualization"
echo "  • python-gntp: Growl notification support"
echo
echo "You can now run TaskCoach with:"
echo -e "  ${BLUE}./taskcoach-run.sh${NC}"
echo
echo "To see all options:"
echo -e "  ${BLUE}./taskcoach-run.sh --help${NC}"
echo
echo "To build a package for installation:"
echo -e "  ${BLUE}./scripts/build-arch.sh${NC}"
echo
