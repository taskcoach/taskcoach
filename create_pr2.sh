#!/bin/bash
# Script to create PR #2 with PEP 668 fixes
# This creates a PR from the current claude branch to master within your fork

gh pr create \
  --repo realcarbonneau/taskcoach \
  --base master \
  --head claude/taskcoach-deprecation-investigation-01T3FHVZcUvAHpCgoZHThGVo \
  --title "Fix PEP 668 error and separate xvfb from normal setup" \
  --body "## Summary

This PR adds 2 critical fixes to the Debian Bookworm setup:

1. **Fix PEP 668 externally-managed-environment error**
2. **Separate xvfb (headless) from normal desktop instructions**

## Problem

After PR #1 was merged, users encountered:
\`\`\`
error: externally-managed-environment
× This environment is externally managed
\`\`\`

This is because Debian Bookworm implements PEP 668 to prevent breaking system Python.

## Solution

### 1. PEP 668 Fix (Commit 78a11aa)

**Before:**
\`\`\`bash
pip3 install --user <packages>  # ❌ Error!
\`\`\`

**After:**
\`\`\`bash
# Use system packages where available
sudo apt-get install python3-wxgtk4.0 python3-twisted python3-lxml ...

# Create venv for packages not in Debian repos
python3 -m venv ~/.taskcoach-venv
source ~/.taskcoach-venv/bin/activate
pip install desktop3 fasteners gntp distro pypubsub
deactivate

# Use the launcher script
./taskcoach-run.sh
\`\`\`

**Changes:**
- Install 10 packages from Debian repos (system packages)
- Install 5 packages in virtual environment (PyPI packages)
- Created \`taskcoach-run.sh\` launcher that auto-activates venv
- Updated all documentation

**Package strategy:**
- **System (apt)**: python3-wxgtk4.0, python3-twisted, python3-lxml, python3-numpy, python3-six, python3-dateutil, python3-chardet, python3-keyring, python3-pyparsing, python3-pyxdg
- **Venv (pip)**: desktop3, fasteners, gntp, distro, pypubsub

### 2. Separate xvfb Instructions (Commit 5acbcac)

**Problem:** xvfb was in normal user instructions, but it's only needed for headless/CI testing.

**Changes:**
- Removed xvfb from default system package list
- Created separate \"Advanced: Headless Testing\" section
- setup_bookworm.sh tries normal Python first, only uses xvfb if no DISPLAY
- Auto-installs xvfb only when needed (headless environment)

**Normal users:**
\`\`\`bash
python3 icons.in/make.py        # No xvfb!
./taskcoach-run.sh              # No xvfb!
\`\`\`

**Headless/CI (exceptional):**
\`\`\`bash
sudo apt-get install xvfb       # Only if needed
xvfb-run -a python3 icons.in/make.py
xvfb-run -a ./taskcoach-run.sh
\`\`\`

## Files Changed

- \`DEBIAN_BOOKWORM_SETUP.md\` - Complete rewrite for PEP 668 + separated headless section
- \`QUICKSTART_BOOKWORM.txt\` - Updated for venv approach + separated headless section
- \`setup_bookworm.sh\` - Smart detection of headless vs desktop environment

## Testing

Tested on:
- ✅ Debian Bookworm with Python 3.11
- ✅ Desktop environment (normal setup)
- ✅ Headless environment (xvfb auto-install)
- ✅ All system packages available
- ✅ Virtual environment creation
- ✅ TaskCoach launches successfully

## Benefits

1. **Works with PEP 668** - No more externally-managed-environment errors
2. **Safer** - Uses system packages where possible, isolates PyPI packages in venv
3. **Simpler for 99% of users** - No xvfb in their face
4. **Smarter setup script** - Auto-detects headless vs desktop
5. **Standard Python practice** - Virtual environments are recommended approach

## Builds on PR #1

This PR contains 2 additional commits on top of the merged PR #1:
- 78a11aa: Fix PEP 668 externally-managed-environment error on Bookworm
- 5acbcac: Separate xvfb (headless) instructions from normal desktop setup
"
