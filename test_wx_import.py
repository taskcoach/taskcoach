#!/usr/bin/env python3
"""Test which hypertreelist file is being imported."""

import sys
print(f"Python executable: {sys.executable}")
print(f"Python path: {sys.path[:3]}")

try:
    import wx
    print(f"wx imported from: {wx.__file__}")
    print(f"wx version: {wx.version()}")

    import wx.lib.agw.hypertreelist as ht
    print(f"hypertreelist imported from: {ht.__file__}")

    # Check if our patches are present
    # Note: PaintItem is overridden in TreeListMainWindow, not in CustomTreeCtrl
    import inspect
    source = inspect.getsource(ht.TreeListMainWindow.PaintItem)

    patches_found = 0

    # Check for Issue #2081 fix (TR_FULL_ROW_HIGHLIGHT)
    if "Fix from Issue #2081 (Roland171281)" in source:
        print("\n✓ Issue #2081 patch PRESENT - TR_FULL_ROW_HIGHLIGHT background fix!")
        patches_found += 1
    else:
        print("\n✗ Issue #2081 patch MISSING - TR_FULL_ROW_HIGHLIGHT won't work!")

    # Check for PR #2088 fix (TR_FILL_WHOLE_COLUMN_BACKGROUND)
    if "Draw full row background BEFORE column loop to avoid clipping issues" in source:
        print("✓ PR #2088 patch PRESENT - TR_FILL_WHOLE_COLUMN_BACKGROUND fix!")
        patches_found += 1
    else:
        print("✗ PR #2088 patch MISSING - Right-aligned columns won't be colored!")

    if patches_found == 2:
        print("\n✓✓ ALL PATCHES VERIFIED - Background coloring should work correctly!")
    else:
        print(f"\n✗ Only {patches_found}/2 patches found - Background coloring may not work correctly!")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
