# TaskCoach on Debian Bookworm - Setup Guide

This guide explains how to test TaskCoach on Debian 12 (Bookworm).

---

## ⚠️ IMPORTANT: wxPython Patch Required

Debian Bookworm ships wxPython 4.2.0, which has critical bugs affecting category row background coloring. This setup automatically applies a patch at step [6/7].

**For complete details, see [CRITICAL_WXPYTHON_PATCH.md](CRITICAL_WXPYTHON_PATCH.md)**

---

## System Requirements

- **OS**: Debian 12 (Bookworm)
- **Python**: 3.11 (default in Bookworm)
- **wxPython**: 4.2.0 (available in Bookworm repos)

## Getting the Code

Choose one of these methods to download TaskCoach:

### Option 1: Shallow Git Clone (Recommended)

Fast download (~70MB), includes git for easy updates:

```bash
cd ~/Downloads
git clone --depth 1 --branch claude/taskcoach-deprecation-investigation-01T3FHVZcUvAHpCgoZHThGVo \
  https://github.com/realcarbonneau/taskcoach.git taskcoach
cd taskcoach
```

**To update later:**
```bash
cd ~/Downloads/taskcoach
git pull
```

### Option 2: Full Git Clone

Complete repository with full history (~400MB):

```bash
cd ~/Downloads
git clone --branch claude/taskcoach-deprecation-investigation-01T3FHVZcUvAHpCgoZHThGVo \
  https://github.com/realcarbonneau/taskcoach.git taskcoach
cd taskcoach
```

### Option 3: Download as ZIP

Smallest download (~50MB), no git required:

```bash
cd ~/Downloads
wget https://github.com/realcarbonneau/taskcoach/archive/refs/heads/claude/taskcoach-deprecation-investigation-01T3FHVZcUvAHpCgoZHThGVo.zip -O taskcoach.zip
unzip taskcoach.zip
mv taskcoach-claude-taskcoach-deprecation-investigation-01T3FHVZcUvAHpCgoZHThGVo taskcoach
rm taskcoach.zip
cd taskcoach
```

**Or with curl:**
```bash
cd ~/Downloads
curl -L https://github.com/realcarbonneau/taskcoach/archive/refs/heads/claude/taskcoach-deprecation-investigation-01T3FHVZcUvAHpCgoZHThGVo.zip -o taskcoach.zip
unzip taskcoach.zip
mv taskcoach-claude-taskcoach-deprecation-investigation-01T3FHVZcUvAHpCgoZHThGVo taskcoach
rm taskcoach.zip
cd taskcoach
```

**Note**: With ZIP download, you need to re-download the entire file to get updates (no `git pull`).

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

#### Step 3: Run TaskCoach

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
python3 -c "import taskcoachlib.meta.data as meta; print('TaskCoach version:', meta.version)"
```

Expected output: `TaskCoach version: 1.5.1`

### Comprehensive Test
```bash
./test_taskcoach.sh
```

This runs 12 tests to verify all dependencies and prerequisites.

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
- ⚠️ python3-pyparsing (3.0.9) - **Note: requires 3.1.3+, install via pip**
- ✅ python3-pyxdg (0.28)

### From PyPI (pip in venv):
- 📦 desktop3
- 📦 lockfile
- 📦 gntp
- 📦 distro
- 📦 pypubsub
- 📦 pyparsing>=3.1.3 (Bookworm's 3.0.9 is too old)

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

- TaskCoach Homepage: https://github.com/realcarbonneau/taskcoach
- GitHub Issues: https://github.com/realcarbonneau/taskcoach/issues
- Documentation: See README.md in the repository

## Compatibility Notes

✅ **Working**: Application starts, GUI loads, basic functionality tested
✅ **Python 3.11**: Fully compatible
✅ **wxPython 4.2.0**: Fully compatible
✅ **PEP 668**: Properly handled with venv approach
⚠️  **Test Suite**: One minor issue with unittest._TextTestResult (doesn't affect app)

Last tested: 2025-11-15 (Updated for PEP 668)
