# TaskCoach on Debian Bookworm - Setup Guide

This guide explains how to test TaskCoach on Debian 12 (Bookworm).

## System Requirements

- **OS**: Debian 12 (Bookworm)
- **Python**: 3.11 (default in Bookworm)
- **wxPython**: 4.2.0 (available in Bookworm repos)

## Important Note About PEP 668

Debian Bookworm implements PEP 668, which prevents `pip install --user` from modifying the system Python environment. This is a **good security feature**. We'll use system packages where possible and a virtual environment for the rest.

## Quick Setup (Recommended)

### Option 1: Automated Setup Script

```bash
# Run the automated setup script
./setup_bookworm.sh

# This will:
# - Install system packages
# - Create a virtual environment
# - Install remaining dependencies
# - Generate icons and templates
```

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
    python3-twisted \
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

For packages not available in Debian repos (desktop3, lockfile, gntp, distro, pypubsub):

```bash
# Set your TaskCoach directory (change this to your actual path)
TASKCOACH_HOME=/path/to/taskcoach

cd "$TASKCOACH_HOME"

# Create virtual environment with access to system packages
python3 -m venv --system-site-packages .venv

# Activate it
source .venv/bin/activate

# Install remaining dependencies
pip install desktop3 lockfile gntp distro pypubsub

# Deactivate when done
deactivate
```

**Note**: The `--system-site-packages` flag allows the virtual environment to access system-installed packages (like wxPython, twisted, lxml) while keeping pip-installed packages isolated. This is the recommended approach for TaskCoach.

#### Step 3: Generate Required Files

TaskCoach needs to generate icons and templates before first run:

```bash
# Set your TaskCoach directory (change this to your actual path)
TASKCOACH_HOME=/path/to/taskcoach

# Generate icons (must run from icons.in directory)
cd "$TASKCOACH_HOME/icons.in"
python3 make.py

# Generate templates (must run from templates.in directory)
cd "$TASKCOACH_HOME/templates.in"
python3 make.py

# Return to project root
cd "$TASKCOACH_HOME"
```

#### Step 4: Run TaskCoach

```bash
# Using the launch script:
./taskcoach-run.sh

# Or manually:
source .venv/bin/activate
python3 taskcoach.py
```

## Testing the Installation

### Quick Test
```bash
python3 -c "import taskcoachlib; print('TaskCoach version:', taskcoachlib.meta.version)"
```

Expected output: `TaskCoach version: 1.5.0`

### Comprehensive Test
```bash
./test_taskcoach.sh
```

This runs 14+ tests to verify everything works.

## Usage Examples

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

## Advanced: Headless/Automated Testing

**Note**: This section is only for running TaskCoach without a display (SSH sessions, automated testing, CI/CD). Normal desktop users can skip this.

### Install xvfb (headless only)

```bash
sudo apt-get install -y xvfb
```

### Generate resources headless

```bash
# Set your TaskCoach directory (change this to your actual path)
TASKCOACH_HOME=/path/to/taskcoach

# Generate icons
cd "$TASKCOACH_HOME/icons.in"
xvfb-run -a python3 make.py

# Generate templates
cd "$TASKCOACH_HOME/templates.in"
xvfb-run -a python3 make.py

# Return to project root
cd "$TASKCOACH_HOME"
```

### Run TaskCoach headless

```bash
xvfb-run -a ./taskcoach-run.sh
```

## Known Issues on Bookworm

### Issue 1: PEP 668 Error
**Symptom**: `error: externally-managed-environment`

**Solution**: Use a virtual environment (as shown above) or system packages.

### Issue 2: wxPython Import Error
**Symptom**: `ModuleNotFoundError: No module named 'wx'`

**Solution**: Install system package:
```bash
sudo apt-get install python3-wxgtk4.0
```

### Issue 3: Missing Icons
**Symptom**: Error message "couldn't import icons.py"

**Solution**: Generate the icons file:
```bash
TASKCOACH_HOME=/path/to/taskcoach  # Change to your path
cd "$TASKCOACH_HOME/icons.in"
python3 make.py
cd "$TASKCOACH_HOME"
```

If running headless/over SSH without a display:
```bash
TASKCOACH_HOME=/path/to/taskcoach  # Change to your path
cd "$TASKCOACH_HOME/icons.in"
xvfb-run -a python3 make.py
cd "$TASKCOACH_HOME"
```

### Issue 4: Missing Templates
**Symptom**: `ModuleNotFoundError: No module named 'taskcoachlib.persistence.xml.templates'`

**Solution**: Generate the templates file:
```bash
TASKCOACH_HOME=~/Downloads/taskcoach-master  # Change to your path
cd "$TASKCOACH_HOME/templates.in"
python3 make.py
cd "$TASKCOACH_HOME"
```

If running headless/over SSH without a display:
```bash
TASKCOACH_HOME=~/Downloads/taskcoach-master  # Change to your path
cd "$TASKCOACH_HOME/templates.in"
xvfb-run -a python3 make.py
cd "$TASKCOACH_HOME"
```

## Package Sources in Bookworm

### From Debian Repositories (apt):
- ✅ python3-wxgtk4.0 (4.2.0)
- ✅ python3-six (1.16.0)
- ✅ python3-twisted (22.4.0)
- ✅ python3-lxml (4.9.2)
- ✅ python3-numpy (1.24.2)
- ✅ python3-dateutil (2.8.2)
- ✅ python3-chardet (5.1.0)
- ✅ python3-keyring (23.13.1)
- ✅ python3-pyparsing (3.0.9)
- ✅ python3-pyxdg (0.28)

### From PyPI (pip in venv):
- 📦 desktop3
- 📦 lockfile
- 📦 gntp
- 📦 distro
- 📦 pypubsub

## Why Virtual Environment?

Debian Bookworm uses PEP 668 to prevent accidental breaking of system Python. Benefits:

- ✅ **Safe**: Won't break system tools
- ✅ **Clean**: Isolated from system packages
- ✅ **Reproducible**: Easy to recreate
- ✅ **Standard**: Recommended Python practice

The small overhead of activating the venv is worth the safety.

## Troubleshooting

### Check Python Version
```bash
python3 --version  # Should be 3.11.x
```

### Check Virtual Environment
```bash
TASKCOACH_HOME=~/Downloads/taskcoach-master  # Change to your path
cd "$TASKCOACH_HOME"
source .venv/bin/activate
pip list | grep -E "(desktop3|lockfile|gntp|distro|pypubsub)"
deactivate
```

### Check System Packages
```bash
dpkg -l | grep python3-wx
apt list --installed | grep python3-twisted
```

### Verbose Logging
```bash
./taskcoach-run.sh --verbose
```

## Uninstall

To remove TaskCoach:

```bash
# Set your TaskCoach directory
TASKCOACH_HOME=/path/to/taskcoach

# Remove TaskCoach directory (includes the venv)
rm -rf "$TASKCOACH_HOME"

# Remove system packages (optional)
sudo apt-get remove python3-wxgtk4.0
```

## Support

- TaskCoach Homepage: http://www.taskcoach.org
- GitHub Issues: https://github.com/taskcoach/taskcoach/issues
- Documentation: See README.md in the repository

## Compatibility Notes

✅ **Working**: Application starts, GUI loads, basic functionality tested
✅ **Python 3.11**: Fully compatible
✅ **wxPython 4.2.0**: Fully compatible
✅ **PEP 668**: Properly handled with venv approach
⚠️  **Test Suite**: One minor issue with unittest._TextTestResult (doesn't affect app)

Last tested: 2025-11-15 (Updated for PEP 668)
