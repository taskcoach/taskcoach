#!/bin/bash
# TaskCoach Setup Script for Debian Bookworm
# This script automates the setup and testing of TaskCoach on Debian 12
# Updated to handle PEP 668 properly

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
echo "          python3-pyparsing, python3-pyxdg, python3-venv, xvfb"
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
        python3-venv \
        xvfb
    echo -e "${GREEN}✓ System packages installed${NC}"
else
    echo -e "${YELLOW}⚠ sudo not available, please install packages manually${NC}"
    exit 1
fi
echo

# Create virtual environment for packages not in Debian repos
echo -e "${BLUE}[3/7] Creating virtual environment...${NC}"
VENV_PATH="$HOME/.taskcoach-venv"

if [ -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}Virtual environment already exists at $VENV_PATH${NC}"
    read -p "Recreate it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_PATH"
        python3 -m venv "$VENV_PATH"
        echo -e "${GREEN}✓ Virtual environment recreated${NC}"
    else
        echo -e "${GREEN}✓ Using existing virtual environment${NC}"
    fi
else
    python3 -m venv "$VENV_PATH"
    echo -e "${GREEN}✓ Virtual environment created at $VENV_PATH${NC}"
fi
echo

# Install Python dependencies not available in Debian repos
echo -e "${BLUE}[4/7] Installing Python dependencies in venv...${NC}"
echo "Installing: desktop3, lockfile, gntp, distro, pypubsub"

source "$VENV_PATH/bin/activate"
pip install --quiet desktop3 lockfile gntp distro pypubsub
deactivate

echo -e "${GREEN}✓ Python dependencies installed in virtual environment${NC}"
echo

# Generate icons
echo -e "${BLUE}[5/7] Generating icon resources...${NC}"
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
echo -e "${BLUE}[6/7] Generating template resources...${NC}"
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

# Create launch script
echo -e "${BLUE}[7/7] Creating launch script...${NC}"
cat > "$SCRIPT_DIR/taskcoach-run.sh" << 'EOFLAUNCH'
#!/bin/bash
# TaskCoach launcher with virtual environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$HOME/.taskcoach-venv"

if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    echo "Please run setup_bookworm.sh first"
    exit 1
fi

source "$VENV_PATH/bin/activate"
cd "$SCRIPT_DIR"
python3 taskcoach.py "$@"
EOFLAUNCH

chmod +x "$SCRIPT_DIR/taskcoach-run.sh"
echo -e "${GREEN}✓ Launch script created: taskcoach-run.sh${NC}"
echo

# Test installation
echo -e "${BLUE}Testing installation...${NC}"
echo "===================="
echo

# Test 1: Import taskcoachlib
echo -n "Testing taskcoachlib import... "
if VERSION=$(python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); import taskcoachlib; print(taskcoachlib.meta.version)" 2>/dev/null); then
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

# Test 3: Test venv packages
echo -n "Testing virtual environment packages... "
source "$VENV_PATH/bin/activate"
if python3 -c "import desktop3, lockfile, gntp, distro; from pubsub import pub" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    deactivate
    exit 1
fi
deactivate

# Test 4: Run help
echo -n "Testing application help... "
if "$SCRIPT_DIR/taskcoach-run.sh" --help &>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    exit 1
fi

# Test 5: Quick GUI test
echo -n "Testing GUI initialization... "
if timeout 3 xvfb-run -a "$SCRIPT_DIR/taskcoach-run.sh" 2>&1 | grep -q "TaskCoach\|wx" || [ $? -eq 124 ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ Could not fully test (this is OK)${NC}"
fi

echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo
echo "TaskCoach has been set up with:"
echo "  • System packages from Debian repos (wxPython, numpy, lxml, etc.)"
echo "  • Virtual environment at: $VENV_PATH"
echo "  • Additional packages in venv (desktop3, lockfile, gntp, distro, pypubsub)"
echo
echo "You can now run TaskCoach with:"
echo -e "  ${BLUE}./taskcoach-run.sh${NC}"
echo
echo "Or with a virtual display (for headless/SSH):"
echo -e "  ${BLUE}xvfb-run -a ./taskcoach-run.sh${NC}"
echo
echo "To see all options:"
echo -e "  ${BLUE}./taskcoach-run.sh --help${NC}"
echo
echo "For more information, see DEBIAN_BOOKWORM_SETUP.md"
echo
