#!/bin/bash

# Script to copy patched wxPython file to venv
# This applies the fix from wxPython PR #2088 for full-row background coloring
#
# Version: 1.1.1.003 (f20c4dc)
# Branch: claude/add-module-loading-logs-01SvgNHroJJfg6fZCGp2mqd5
# Last Updated: 2025-11-16

set -e

echo "=========================================="
echo "Applying wxPython Patch to venv"
echo "Version 1.1.1.003 (f20c4dc)"
echo "=========================================="
echo ""

# Check if venv exists
if [ ! -d ".venv" ]; then
    echo "✗ ERROR: .venv directory not found"
    echo "  Please create the virtual environment first:"
    echo "  python3 -m venv --system-site-packages .venv"
    exit 1
fi

# Determine Python version
PYTHON_VERSION=$(.venv/bin/python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python version: $PYTHON_VERSION"

# Create target directory structure
TARGET_DIR=".venv/lib/python${PYTHON_VERSION}/site-packages/wx/lib/agw"
echo "Creating directory: $TARGET_DIR"
mkdir -p "$TARGET_DIR"

# Copy patched file
SOURCE_FILE="patches/wxpython/hypertreelist.py"
TARGET_FILE="$TARGET_DIR/hypertreelist.py"

if [ ! -f "$SOURCE_FILE" ]; then
    echo "✗ ERROR: Patched file not found: $SOURCE_FILE"
    exit 1
fi

echo "Copying patched file..."
cp "$SOURCE_FILE" "$TARGET_FILE"

# Verify the patch
if grep -q "itemrect = wx.Rect(0, item.GetY() + off_h, total_w-1, total_h - off_h)" "$TARGET_FILE"; then
    echo "✓ Patch verified successfully!"
else
    echo "✗ WARNING: Could not verify patch in target file"
    exit 1
fi

# Create usercustomize.py to enable the import hook
USERCUSTOMIZE_FILE=".venv/lib/python${PYTHON_VERSION}/site-packages/usercustomize.py"
echo "Creating import hook: $USERCUSTOMIZE_FILE"

cat > "$USERCUSTOMIZE_FILE" << 'EOF'
"""
Custom site configuration to inject patched wxPython hypertreelist module.

This file is automatically executed by Python on startup when running in this venv.
It replaces the system wx.lib.agw.hypertreelist module with our patched version
that fixes full-row background coloring issues.
"""

import sys
import os
from importlib.abc import MetaPathFinder
from importlib.util import spec_from_file_location


class WxPatchFinder(MetaPathFinder):
    """Import hook to replace wx.lib.agw.hypertreelist with patched version."""

    def find_spec(self, fullname, path, target=None):
        if fullname == 'wx.lib.agw.hypertreelist':
            # Path to our patched file
            venv_path = sys.prefix
            patched_file = os.path.join(
                venv_path, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}',
                'site-packages', 'wx', 'lib', 'agw', 'hypertreelist.py'
            )

            if os.path.exists(patched_file):
                spec = spec_from_file_location(fullname, patched_file)
                return spec

        return None


# Install the import hook at the VERY BEGINNING of sys.meta_path
# This ensures it's checked before the standard import machinery
if not any(isinstance(finder, WxPatchFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, WxPatchFinder())
EOF

echo "✓ Import hook installed!"

echo ""
echo "=========================================="
echo "Patch Applied Successfully!"
echo "=========================================="
echo ""
echo "The patched wxPython file has been installed to:"
echo "  $TARGET_FILE"
echo ""
echo "This file will override the system wxPython when running"
echo "Task Coach from this venv, providing full-row background"
echo "coloring for all columns."
echo ""
echo "Next steps:"
echo "1. Run Task Coach: ./taskcoach-run.sh"
echo "2. Test background coloring on categories and tasks"
echo ""
