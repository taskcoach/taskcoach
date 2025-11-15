# TaskCoach on Debian Bookworm - Setup Guide

This guide explains how to test TaskCoach on Debian 12 (Bookworm).

## System Requirements

- **OS**: Debian 12 (Bookworm)
- **Python**: 3.11 (default in Bookworm)
- **wxPython**: 4.2.0 (available in Bookworm repos)

## Quick Setup

### 1. Install System Dependencies

```bash
# Update package list
sudo apt-get update

# Install wxPython and required system packages
sudo apt-get install -y python3-wxgtk4.0 python3-pip python3-dev

# Optional: Install xvfb if you want to test without a display
sudo apt-get install -y xvfb
```

### 2. Install Python Dependencies

```bash
# Install required Python packages
pip3 install --user six desktop3 pypubsub twisted chardet lxml \
    pyxdg keyring numpy lockfile gntp distro python-dateutil

# Or use the requirements.txt
pip3 install --user -r requirements.txt
```

### 3. Generate Required Files

TaskCoach needs to generate icons and templates before first run:

```bash
# If you have a display:
cd /path/to/taskcoach
python3 icons.in/make.py
python3 templates.in/make.py

# OR if running headless/SSH (using Xvfb):
cd /path/to/taskcoach
xvfb-run -a python3 icons.in/make.py
xvfb-run -a python3 templates.in/make.py
```

### 4. Run TaskCoach

```bash
# With a display:
python3 taskcoach.py

# OR headless/SSH (using Xvfb):
xvfb-run -a python3 taskcoach.py

# Show help:
python3 taskcoach.py --help

# Open a specific task file:
python3 taskcoach.py mytasks.tsk
```

## Alternative: Using the Automated Setup Script

Use the included `setup_bookworm.sh` script:

```bash
chmod +x setup_bookworm.sh
./setup_bookworm.sh
```

## Testing the Installation

### 1. Test Basic Import
```bash
python3 -c "import taskcoachlib; print('TaskCoach version:', taskcoachlib.meta.version)"
```

Expected output: `TaskCoach version: 1.5.0`

### 2. Test wxPython
```bash
python3 -c "import wx; print('wxPython version:', wx.__version__)"
```

Expected output: `wxPython version: 4.2.0` (or similar)

### 3. Test Application Launch
```bash
# Show help (doesn't require display)
python3 taskcoach.py --help

# Test GUI (requires display or xvfb)
timeout 5 xvfb-run -a python3 taskcoach.py &
sleep 2
ps aux | grep taskcoach
killall python3
```

## Known Issues on Bookworm

### Issue 1: wxPython Version Mismatch
**Symptom**: `ModuleNotFoundError: No module named 'wx._core'`

**Solution**: Ensure you're using Python 3.11 (Bookworm default), as the system wxPython package is built for 3.11:
```bash
python3 --version  # Should show 3.11.x
which python3      # Should be /usr/bin/python3
```

### Issue 2: Missing Icons
**Symptom**: Error message "couldn't import icons.py"

**Solution**: Generate the icons file:
```bash
cd /path/to/taskcoach
xvfb-run -a python3 icons.in/make.py
```

### Issue 3: Missing Templates
**Symptom**: `ModuleNotFoundError: No module named 'taskcoachlib.persistence.xml.templates'`

**Solution**: Generate the templates file:
```bash
cd /path/to/taskcoach
xvfb-run -a python3 templates.in/make.py
```

### Issue 4: No Display Available
**Symptom**: "Unable to access the X Display, is $DISPLAY set properly?"

**Solution**: Either:
- Run on a system with a graphical display
- Use SSH with X11 forwarding: `ssh -X user@host`
- Use Xvfb: `xvfb-run -a python3 taskcoach.py`
- Use VNC or similar remote desktop

## Package Versions in Bookworm

For reference, these are the expected versions:

- Python: 3.11.2+
- python3-wxgtk4.0: 4.2.0+dfsg-3
- python3-twisted: 22.4.0+
- python3-lxml: 4.9.2+
- python3-numpy: 1.24.2+

## Troubleshooting

### Check Python Path
```bash
python3 -c "import sys; print('\n'.join(sys.path))"
```

### Check Installed Packages
```bash
pip3 list | grep -E "(wx|twisted|lxml|numpy|pypubsub)"
dpkg -l | grep python3-wx
```

### Verbose Logging
```bash
python3 taskcoach.py --verbose
```

## Building from Source (Advanced)

If you prefer to build wxPython from source (not recommended):

```bash
# Install build dependencies
sudo apt-get install -y build-essential python3-dev libgtk-3-dev \
    libwebkit2gtk-4.0-dev libjpeg-dev libtiff-dev libsdl2-dev \
    libnotify-dev freeglut3-dev libsm-dev

# This will take 30+ minutes
pip3 install --user wxPython
```

## Support

- TaskCoach Homepage: http://www.taskcoach.org
- GitHub Issues: https://github.com/taskcoach/taskcoach/issues
- Documentation: See README.md in the repository

## Compatibility Notes

✅ **Working**: Application starts, GUI loads, basic functionality tested
✅ **Python 3.11**: Fully compatible
✅ **wxPython 4.2.0**: Fully compatible
⚠️  **Test Suite**: One minor issue with unittest._TextTestResult (doesn't affect app)

Last tested: 2025-11-15
