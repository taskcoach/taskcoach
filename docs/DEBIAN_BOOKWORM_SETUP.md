# TaskCoach on Debian Bookworm - Setup Guide

This guide explains how to install and run TaskCoach on Debian 12 (Bookworm).

---

## Quick Start: Install the .deb Package (Recommended)

The easiest way to install TaskCoach on Debian Bookworm is using the pre-built `.deb` package:

```bash
# Download the latest .deb from GitHub releases
wget https://github.com/realcarbonneau/taskcoach/releases/latest/download/taskcoach_1.6.1_all.deb

# Install it (this will also install dependencies)
sudo apt install ./taskcoach_1.6.1_all.deb

# Run TaskCoach
taskcoach
```

That's it! The .deb package handles all dependencies and the wxPython patch automatically.

### What the .deb Package Includes

- All Python dependencies from Debian repositories
- Bundled wxPython patch for category row coloring (see [CRITICAL_WXPYTHON_PATCH.md](CRITICAL_WXPYTHON_PATCH.md))
- Desktop integration (application menu entry, file associations)
- Man page

### Uninstalling

```bash
sudo apt remove taskcoach
```

---

## Building the .deb Package Yourself

If you want to build the package from source:

```bash
# Install build dependencies
sudo apt install build-essential debhelper dh-python python3-all python3-setuptools devscripts

# Clone the repository
git clone https://github.com/realcarbonneau/taskcoach.git
cd taskcoach

# Build the package
dpkg-buildpackage -us -uc -b

# Install the built package
sudo apt install ../taskcoach_*.deb
```

For more details on the packaging system, see [PACKAGING.md](PACKAGING.md).

---

## Development Setup (Running from Source)

This section is for developers who want to work on TaskCoach code. If you just want to use TaskCoach, install the .deb package above.

### ⚠️ IMPORTANT: wxPython Patch Required

Debian Bookworm ships wxPython 4.2.0, which has critical bugs affecting category row background coloring. When running from source, the patch is applied automatically via the import hook.

**For complete details, see [CRITICAL_WXPYTHON_PATCH.md](CRITICAL_WXPYTHON_PATCH.md)**

### System Requirements

- **OS**: Debian 12 (Bookworm)
- **Python**: 3.11 (default in Bookworm)
- **wxPython**: 4.2.0 (available in Bookworm repos)

### Getting the Code

```bash
# Clone the repository (shallow clone to save space)
git clone --depth 1 https://github.com/realcarbonneau/taskcoach.git
cd taskcoach
```

### Updating to Latest Version

```bash
cd ~/Downloads/taskcoach  # or wherever you cloned it
git fetch --depth=1 origin master
git checkout FETCH_HEAD
```

This fetches only the latest commit without downloading full history.

### Important Note About PEP 668

Debian Bookworm implements PEP 668, which prevents `pip install --user` from modifying the system Python environment. This is a **good security feature**. We'll use system packages where possible and a virtual environment for the rest.

### Option 1: Automated Setup Script (Recommended for Development)

```bash
# Auto-detect your OS and run appropriate setup
./setup.sh

# Or explicitly run for Debian 12:
./setup_debian12_bookworm.sh

# This will:
# - Install system packages
# - Create a virtual environment
# - Install remaining dependencies

# Run TaskCoach
./taskcoach-run.sh
```

**Available setup scripts:**
- `setup.sh` - Auto-detects OS and runs appropriate script
- `setup_debian12_bookworm.sh` - Debian 12 (Bookworm)
- `setup_debian13_trixie.sh` - Debian 13 (Trixie)
- `setup_ubuntu2204_jammy.sh` - Ubuntu 22.04 (Jammy)
- `setup_ubuntu2404_noble.sh` - Ubuntu 24.04 (Noble)

### Option 2: Manual Setup

Follow these steps if you prefer manual installation:

#### Step 1: Install System Dependencies

```bash
# Update package list
sudo apt-get update

# Install wxPython and available Python packages from Debian repos
sudo apt-get install -y \
    python3-wxgtk4.0 \
    python3-six \
    python3-lxml \
    python3-numpy \
    python3-dateutil \
    python3-chardet \
    python3-keyring \
    python3-pyparsing \
    python3-pyxdg \
    python3-venv
```

#### Step 2: Create Virtual Environment

For packages not available in Debian repos (desktop3, fasteners, gntp, distro, pypubsub, watchdog):

```bash
cd /path/to/taskcoach

# Create virtual environment with access to system packages
python3 -m venv --system-site-packages .venv

# Activate it
source .venv/bin/activate

# Install remaining dependencies
pip install desktop3 fasteners gntp distro pypubsub 'watchdog>=3.0.0'

# Deactivate when done
deactivate
```

**Note**: The `--system-site-packages` flag allows the virtual environment to access system-installed packages (like wxPython, lxml, numpy) while keeping pip-installed packages isolated.

#### Step 3: Run TaskCoach

```bash
# Using the launch script:
./taskcoach-run.sh

# Or manually:
source .venv/bin/activate
python3 taskcoach.py
```

### Testing the Installation

#### Quick Test
```bash
python3 -c "import taskcoachlib.meta.data as meta; print('TaskCoach version:', meta.version)"
```

#### Comprehensive Test
```bash
./test_taskcoach.sh
```

This runs tests to verify all dependencies and prerequisites.

### Usage Examples

```bash
# Show help
./taskcoach-run.sh --help

# Start with GUI
./taskcoach-run.sh

# Open specific file
./taskcoach-run.sh mytasks.tsk

# Use custom settings
./taskcoach-run.sh --ini=/path/to/settings.ini

# Use different language
./taskcoach-run.sh --language=fr
```

---

## Advanced: Headless/Automated Testing

**Note**: This section is only for running TaskCoach without a display (SSH sessions, automated testing, CI/CD). Normal desktop users can skip this.

### Install xvfb (headless only)

```bash
sudo apt-get install -y xvfb
```

### Run TaskCoach headless

```bash
xvfb-run -a ./taskcoach-run.sh
```

---

## Troubleshooting

### PEP 668 Error
**Symptom**: `error: externally-managed-environment`

**Solution**: Use a virtual environment (as shown in Development Setup) or install the .deb package.

### wxPython Import Error
**Symptom**: `ModuleNotFoundError: No module named 'wx'`

**Solution**: Install system package:
```bash
sudo apt-get install python3-wxgtk4.0
```

### Missing Templates (Development Only)
**Symptom**: `ModuleNotFoundError: No module named 'taskcoachlib.persistence.xml.templates'`

**Solution**: Generate the templates file:
```bash
cd /path/to/taskcoach/templates.in
python3 make.py
```

### Check Python Version
```bash
python3 --version  # Should be 3.11.x
```

### Check System Packages
```bash
dpkg -l | grep python3-wx
dpkg -l | grep python3-lxml
```

### Verbose Logging
```bash
./taskcoach-run.sh --verbose
```

---

## Package Sources in Bookworm

### From Debian Repositories (apt):
- ✅ python3-wxgtk4.0 (4.2.0)
- ✅ python3-six (1.16.0)
- ✅ python3-lxml (4.9.2)
- ✅ python3-numpy (1.24.2)
- ✅ python3-dateutil (2.8.2)
- ✅ python3-chardet (5.1.0)
- ✅ python3-keyring (23.13.1)
- ⚠️ python3-pyparsing (3.0.9) - **Note: requires 3.1.3+, install via pip**
- ✅ python3-pyxdg (0.28)

### From PyPI (pip in venv, for development):
- 📦 desktop3
- 📦 fasteners
- 📦 gntp
- 📦 distro
- 📦 pypubsub
- 📦 pyparsing>=3.1.3 (Bookworm's 3.0.9 is too old)
- 📦 watchdog>=3.0.0 (Bookworm's 2.2.1 is too old)

---

## Support

- TaskCoach Homepage: https://github.com/realcarbonneau/taskcoach
- GitHub Issues: https://github.com/realcarbonneau/taskcoach/issues
- Documentation: See README.md in the repository

## Related Documentation

- [PACKAGING.md](PACKAGING.md) - Debian packaging details and build process
- [CRITICAL_WXPYTHON_PATCH.md](CRITICAL_WXPYTHON_PATCH.md) - wxPython patch information

## Compatibility Notes

✅ **Working**: Application starts, GUI loads, all functionality tested
✅ **Python 3.11**: Fully compatible
✅ **wxPython 4.2.0**: Compatible (with bundled patch)
✅ **PEP 668**: Properly handled

Last tested: 2025-12-17
