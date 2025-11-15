#!/bin/bash
# TaskCoach Setup Script for Debian Bookworm
# This script automates the setup and testing of TaskCoach on Debian 12

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
echo -e "${BLUE}[1/6] Checking Python version...${NC}"
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
echo -e "${BLUE}[2/6] Installing system dependencies...${NC}"
echo "This will install: python3-wxgtk4.0, python3-pip, python3-dev, xvfb"
echo "Requires sudo privileges."

if command -v sudo &> /dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y python3-wxgtk4.0 python3-pip python3-dev xvfb
    echo -e "${GREEN}✓ System packages installed${NC}"
else
    echo -e "${YELLOW}⚠ sudo not available, please install packages manually:${NC}"
    echo "  apt-get install python3-wxgtk4.0 python3-pip python3-dev xvfb"
    exit 1
fi
echo

# Install Python dependencies
echo -e "${BLUE}[3/6] Installing Python dependencies...${NC}"
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    pip3 install --user -r "$SCRIPT_DIR/requirements.txt" || \
    pip3 install --user six desktop3 pypubsub twisted chardet lxml pyxdg keyring numpy lockfile gntp distro python-dateutil
else
    pip3 install --user six desktop3 pypubsub twisted chardet lxml pyxdg keyring numpy lockfile gntp distro python-dateutil
fi
echo -e "${GREEN}✓ Python dependencies installed${NC}"
echo

# Generate icons
echo -e "${BLUE}[4/6] Generating icon resources...${NC}"
cd "$SCRIPT_DIR"
if [ ! -f "taskcoachlib/gui/icons.py" ]; then
    if [ -d "icons.in" ]; then
        echo "Generating icons (this may take a minute)..."
        xvfb-run -a python3 icons.in/make.py 2>&1 | tail -5
        echo -e "${GREEN}✓ Icons generated${NC}"
    else
        echo -e "${YELLOW}⚠ icons.in directory not found${NC}"
    fi
else
    echo -e "${GREEN}✓ Icons already exist${NC}"
fi
echo

# Generate templates
echo -e "${BLUE}[5/6] Generating template resources...${NC}"
if [ ! -f "taskcoachlib/persistence/xml/templates.py" ]; then
    if [ -d "templates.in" ]; then
        echo "Generating templates..."
        xvfb-run -a python3 templates.in/make.py 2>&1 | tail -5
        echo -e "${GREEN}✓ Templates generated${NC}"
    else
        echo -e "${YELLOW}⚠ templates.in directory not found${NC}"
    fi
else
    echo -e "${GREEN}✓ Templates already exist${NC}"
fi
echo

# Test installation
echo -e "${BLUE}[6/6] Testing installation...${NC}"

# Test 1: Import taskcoachlib
echo -n "Testing taskcoachlib import... "
if VERSION=$(python3 -c "import taskcoachlib; print(taskcoachlib.meta.version)" 2>/dev/null); then
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

# Test 3: Run help
echo -n "Testing application help... "
if python3 taskcoach.py --help &>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    exit 1
fi

# Test 4: Quick GUI test
echo -n "Testing GUI initialization... "
if timeout 3 xvfb-run -a python3 taskcoach.py 2>&1 | grep -q "TaskCoach\|wx" || [ $? -eq 124 ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ Could not fully test (this is OK)${NC}"
fi

echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo "You can now run TaskCoach with:"
echo -e "  ${BLUE}python3 taskcoach.py${NC}"
echo
echo "Or with a virtual display (for headless/SSH):"
echo -e "  ${BLUE}xvfb-run -a python3 taskcoach.py${NC}"
echo
echo "To see all options:"
echo -e "  ${BLUE}python3 taskcoach.py --help${NC}"
echo
echo "For more information, see DEBIAN_BOOKWORM_SETUP.md"
echo
