#!/bin/bash
# Script to create a Pull Request in your fork (realcarbonneau/taskcoach)
# This creates a PR from the claude branch to master within your own repository

gh pr create \
  --repo realcarbonneau/taskcoach \
  --base master \
  --head claude/taskcoach-deprecation-investigation-01T3FHVZcUvAHpCgoZHThGVo \
  --title "Add Debian Bookworm/Trixie compatibility guides and setup tools" \
  --body "## Summary

This PR adds comprehensive documentation and automation tools for running TaskCoach on Debian systems, specifically targeting Debian 12 (Bookworm) and Trixie.

## Investigation Results

TaskCoach **IS compatible** with modern Debian Python requirements:
- ✅ Works with Python 3.11 (Bookworm) and 3.12 (Trixie)
- ✅ Compatible with wxPython 4.2.0+ from Debian repos
- ✅ All dependencies available and working
- ✅ Application runs successfully

## Files Added

### Documentation
- **DEBIAN_BOOKWORM_SETUP.md** - Comprehensive setup guide with troubleshooting
- **QUICKSTART_BOOKWORM.txt** - Quick reference for getting started
- **DEBIAN_COMPARISON.md** - Comparison of Bookworm vs Trixie setups

### Automation Scripts
- **setup_bookworm.sh** - Automated installation and setup script
- **test_taskcoach.sh** - Comprehensive test suite (14+ tests)

## Key Findings

### Recommended: Debian Bookworm
- Simpler setup (Python 3.11 + wxPython 4.2.0 aligned)
- Stable, well-tested package combinations
- No version conflicts

### Also Works: Trixie/Sid
- Requires explicit Python 3.12 usage
- wxPython built for 3.12 while 3.11 may be default
- More complex but functional

## Usage

Quick setup on Debian Bookworm:
\`\`\`bash
./setup_bookworm.sh
python3 taskcoach.py
\`\`\`

Or manual setup:
\`\`\`bash
sudo apt-get install python3-wxgtk4.0
pip3 install --user -r requirements.txt
xvfb-run -a python3 icons.in/make.py
xvfb-run -a python3 templates.in/make.py
python3 taskcoach.py
\`\`\`

## Testing

Run the test suite:
\`\`\`bash
./test_taskcoach.sh
\`\`\`

## Compatibility Notes

- Python 3.8-3.12: Supported
- wxPython 4.2.0+: Required and working
- Debian Bookworm: Recommended (simpler)
- Debian Trixie: Supported (requires python3.12)

## Minor Issues Found

One test suite issue (doesn't affect main app):
- \`tests/test.py:137\` uses deprecated \`unittest._TextTestResult\`
- Should use \`unittest.TextTestResult\` instead
- Only impacts test runner, not TaskCoach itself

## Impact

This makes it easy for Debian users to:
1. Install TaskCoach with confidence
2. Troubleshoot common issues
3. Verify their installation works
4. Understand which Debian version to use

The deprecation from Debian appears to have been due to maintenance concerns rather than Python 3 incompatibility, as the codebase has already been ported successfully.

## Files Changed

- DEBIAN_BOOKWORM_SETUP.md
- QUICKSTART_BOOKWORM.txt
- DEBIAN_COMPARISON.md
- setup_bookworm.sh
- test_taskcoach.sh
"
