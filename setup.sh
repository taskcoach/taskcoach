#!/bin/bash
# TaskCoach Unified Setup Script
# Automatically detects the distribution and sets up TaskCoach appropriately
#
# Supports:
#   - Debian 12 (Bookworm)
#   - Debian 13 (Trixie)
#   - Ubuntu 22.04+ (Jammy and later)
#   - Arch/Manjaro Linux
#   - Fedora 39/40
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

# Detect distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO_ID="$ID"
        DISTRO_VERSION="$VERSION_ID"
        DISTRO_CODENAME="$VERSION_CODENAME"
        DISTRO_NAME="$PRETTY_NAME"
    elif [ -f /etc/debian_version ]; then
        DISTRO_ID="debian"
        DISTRO_VERSION=$(cat /etc/debian_version)
        DISTRO_CODENAME="unknown"
        DISTRO_NAME="Debian $DISTRO_VERSION"
    else
        DISTRO_ID="unknown"
        DISTRO_VERSION="unknown"
        DISTRO_CODENAME="unknown"
        DISTRO_NAME="Unknown Distribution"
    fi
}

# Detect the correct Python version to use
detect_python() {
    # Distribution default Python versions:
    # - Debian 12 Bookworm: Python 3.11
    # - Debian 13 Trixie: Python 3.13
    # - Ubuntu 22.04 Jammy: Python 3.10
    # - Ubuntu 24.04 Noble: Python 3.12
    # All use the default python3, wxPython is built for the default version
    PYTHON_CMD="python3"

    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
}

# Check if distribution is supported
check_supported() {
    case "$DISTRO_ID" in
        debian)
            case "$DISTRO_CODENAME" in
                bookworm|trixie|sid)
                    return 0
                    ;;
                *)
                    echo -e "${YELLOW}Warning: Debian $DISTRO_CODENAME may not be fully supported${NC}"
                    return 0
                    ;;
            esac
            ;;
        ubuntu)
            # Ubuntu 22.04+ should work
            if [ "${DISTRO_VERSION%%.*}" -ge 22 ] 2>/dev/null; then
                return 0
            else
                echo -e "${YELLOW}Warning: Ubuntu $DISTRO_VERSION may not be fully supported (22.04+ recommended)${NC}"
                return 0
            fi
            ;;
        linuxmint|pop)
            echo -e "${YELLOW}Note: $DISTRO_NAME is Ubuntu-based, using Ubuntu setup${NC}"
            DISTRO_ID="ubuntu"
            return 0
            ;;
        manjaro|arch)
            echo -e "${BLUE}Detected Arch-based system: $DISTRO_NAME${NC}"
            echo -e "${BLUE}Redirecting to Arch setup script...${NC}"
            echo
            if [ -f "$SCRIPT_DIR/setup_arch.sh" ]; then
                exec "$SCRIPT_DIR/setup_arch.sh"
            else
                echo -e "${RED}✗ setup_arch.sh not found${NC}"
                exit 1
            fi
            ;;
        endeavouros|garuda|artix|arcolinux)
            echo -e "${YELLOW}Note: $DISTRO_NAME is Arch-based, using Arch setup${NC}"
            if [ -f "$SCRIPT_DIR/setup_arch.sh" ]; then
                exec "$SCRIPT_DIR/setup_arch.sh"
            else
                echo -e "${RED}✗ setup_arch.sh not found${NC}"
                exit 1
            fi
            ;;
        fedora)
            echo -e "${BLUE}Detected Fedora: $DISTRO_NAME${NC}"
            echo -e "${BLUE}Redirecting to Fedora setup script...${NC}"
            echo
            if [ -f "$SCRIPT_DIR/setup_fedora.sh" ]; then
                exec "$SCRIPT_DIR/setup_fedora.sh"
            else
                echo -e "${RED}✗ setup_fedora.sh not found${NC}"
                exit 1
            fi
            ;;
        *)
            echo -e "${YELLOW}Warning: $DISTRO_NAME is not officially supported${NC}"
            echo -e "${YELLOW}This script is designed for Debian/Ubuntu/Arch/Fedora-based systems${NC}"
            read -p "Continue anyway? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
            return 0
            ;;
    esac
}

# Get distribution-specific packages
get_system_packages() {
    # Core packages available on all Debian/Ubuntu systems
    SYSTEM_PACKAGES="python3-wxgtk4.0 python3-six python3-lxml python3-numpy"
    SYSTEM_PACKAGES="$SYSTEM_PACKAGES python3-dateutil python3-chardet python3-keyring"
    SYSTEM_PACKAGES="$SYSTEM_PACKAGES python3-pyparsing python3-pyxdg python3-venv"

    # Distribution-specific additions
    case "$DISTRO_CODENAME" in
        trixie|sid)
            # Trixie has newer packages, add python3.12-venv if needed
            if [ "$PYTHON_CMD" = "python3.12" ]; then
                SYSTEM_PACKAGES="$SYSTEM_PACKAGES python3.12-venv"
            fi
            # Trixie has python3-fasteners and python3-watchdog in repos
            SYSTEM_PACKAGES="$SYSTEM_PACKAGES python3-fasteners python3-watchdog python3-pubsub"
            ;;
        bookworm)
            # Bookworm needs some packages from pip (older versions in repos)
            ;;
        *)
            # Ubuntu and others - check what's available
            ;;
    esac

    echo "$SYSTEM_PACKAGES"
}

# Get pip packages needed (not available or too old in system repos)
get_pip_packages() {
    case "$DISTRO_CODENAME" in
        trixie|sid)
            # Trixie has most packages in repos, only need a few from pip
            echo "desktop3 gntp distro 'pyparsing>=3.1.3' squaremap"
            ;;
        bookworm)
            # Bookworm needs more packages from pip
            # Note: fasteners replaces deprecated lockfile for cross-platform file locking
            echo "desktop3 fasteners gntp distro pypubsub zeroconf 'pyparsing>=3.1.3' squaremap 'watchdog>=3.0.0'"
            ;;
        *)
            # Default: install most from pip to be safe
            echo "desktop3 fasteners gntp distro pypubsub zeroconf 'pyparsing>=3.1.3' squaremap 'watchdog>=3.0.0'"
            ;;
    esac
}

# Main setup function
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}TaskCoach Unified Setup Script${NC}"
    echo -e "${BLUE}Version 1.3.0${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo

    # Step 1: Detect distribution
    echo -e "${BLUE}[1/7] Detecting distribution...${NC}"
    detect_distro
    echo "Detected: $DISTRO_NAME"
    echo "  ID: $DISTRO_ID"
    echo "  Version: $DISTRO_VERSION"
    echo "  Codename: $DISTRO_CODENAME"
    check_supported
    echo -e "${GREEN}✓ Distribution check passed${NC}"
    echo

    # Step 2: Detect Python version
    echo -e "${BLUE}[2/7] Checking Python version...${NC}"
    detect_python
    echo "Using: $PYTHON_CMD (version $PYTHON_VERSION)"

    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
        echo -e "${GREEN}✓ Python version is compatible${NC}"
    else
        echo -e "${RED}✗ Python 3.11+ required, found $PYTHON_VERSION${NC}"
        exit 1
    fi
    echo

    # Step 3: Install system dependencies
    echo -e "${BLUE}[3/7] Installing system dependencies...${NC}"
    SYSTEM_PACKAGES=$(get_system_packages)
    echo "Installing: $SYSTEM_PACKAGES"
    echo "Requires sudo privileges."

    if command -v sudo &> /dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y $SYSTEM_PACKAGES
        echo -e "${GREEN}✓ System packages installed${NC}"
    else
        echo -e "${YELLOW}⚠ sudo not available, please install packages manually${NC}"
        exit 1
    fi
    echo

    # Step 4: Create virtual environment
    echo -e "${BLUE}[4/7] Creating virtual environment...${NC}"
    VENV_PATH="$SCRIPT_DIR/.venv"

    if [ -d "$VENV_PATH" ]; then
        echo -e "${YELLOW}Virtual environment already exists at $VENV_PATH${NC}"
        read -p "Recreate it? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$VENV_PATH"
            $PYTHON_CMD -m venv --system-site-packages "$VENV_PATH"
            echo -e "${GREEN}✓ Virtual environment recreated${NC}"
        else
            echo -e "${GREEN}✓ Using existing virtual environment${NC}"
        fi
    else
        $PYTHON_CMD -m venv --system-site-packages "$VENV_PATH"
        echo -e "${GREEN}✓ Virtual environment created${NC}"
    fi
    echo

    # Step 5: Install pip packages
    echo -e "${BLUE}[5/7] Installing Python dependencies in venv...${NC}"
    PIP_PACKAGES=$(get_pip_packages)
    echo "Installing: $PIP_PACKAGES"

    source "$VENV_PATH/bin/activate"
    eval pip install --quiet $PIP_PACKAGES
    deactivate

    echo -e "${GREEN}✓ Python dependencies installed${NC}"
    echo

    # Step 6: Check launch script
    echo -e "${BLUE}[6/7] Checking launch script...${NC}"
    if [ -f "$SCRIPT_DIR/taskcoach-run.sh" ]; then
        chmod +x "$SCRIPT_DIR/taskcoach-run.sh"
        echo -e "${GREEN}✓ Launch script is ready: taskcoach-run.sh${NC}"
    else
        echo -e "${RED}✗ Launch script not found${NC}"
        echo "taskcoach-run.sh should be included in the repository"
        exit 1
    fi
    echo

    # Step 7: Apply wxPython patch (if needed)
    echo -e "${BLUE}[7/7] Applying wxPython patch...${NC}"
    if [ -f "$SCRIPT_DIR/apply-wxpython-patch.sh" ]; then
        "$SCRIPT_DIR/apply-wxpython-patch.sh"
    else
        echo -e "${YELLOW}⚠ Warning: apply-wxpython-patch.sh not found${NC}"
        echo "  Category row background coloring may not work correctly"
    fi
    echo

    # Testing
    echo -e "${BLUE}Testing installation...${NC}"
    echo "===================="
    echo

    # Test 1: Import taskcoachlib
    echo -n "Testing taskcoachlib import... "
    source "$VENV_PATH/bin/activate"
    if VERSION=$($PYTHON_CMD -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); import taskcoachlib.meta.data as meta; print(meta.version)" 2>/dev/null); then
        echo -e "${GREEN}✓ (version $VERSION)${NC}"
    else
        echo -e "${RED}✗ Failed${NC}"
        deactivate
        exit 1
    fi

    # Test 2: Import wx
    echo -n "Testing wxPython import... "
    if WX_VERSION=$($PYTHON_CMD -c "import wx; print(wx.__version__)" 2>/dev/null); then
        echo -e "${GREEN}✓ (version $WX_VERSION)${NC}"
    else
        echo -e "${RED}✗ Failed${NC}"
        echo "Please check python3-wxgtk4.0 installation"
        deactivate
        exit 1
    fi

    # Test 3: Test key packages
    echo "Testing key packages..."
    FAILED=0
    for pkg in "fasteners" "desktop" "gntp" "distro"; do
        echo -n "  - $pkg... "
        if $PYTHON_CMD -c "import $pkg" 2>/dev/null; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${RED}✗ Failed${NC}"
            FAILED=1
        fi
    done

    # Test pubsub
    echo -n "  - pypubsub... "
    if $PYTHON_CMD -c "from pubsub import pub" 2>/dev/null; then
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
    echo "TaskCoach has been set up for $DISTRO_NAME with:"
    echo "  • Python: $PYTHON_CMD ($PYTHON_VERSION)"
    echo "  • Virtual environment at: $VENV_PATH"
    echo "  • System packages from $DISTRO_ID repos"
    echo "  • Additional packages from pip"
    echo
    echo "You can now run TaskCoach with:"
    echo -e "  ${BLUE}./taskcoach-run.sh${NC}"
    echo
    echo "To see all options:"
    echo -e "  ${BLUE}./taskcoach-run.sh --help${NC}"
    echo
}

main "$@"
