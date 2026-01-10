# Issue #159: Search Dropdown Shows at Far Left of Pane

GitHub Issue: https://github.com/taskcoach/taskcoach/issues/159

## Problem

On Wayland, clicking the search control's magnifier dropdown button causes the menu to appear at the far left of the AUI pane instead of directly below the search control.

## Environment

Tested on Kubuntu 24 with KDE Plasma + Wayland.

## Attempted Fixes (Failed)

1. **Remove coordinate forcing** - Changed from explicit coordinates to no coordinates:
   ```python
   # Before (legacy 2011 code)
   rect = self.GetClientRect()
   x, y = rect[0], rect[1] + rect[3] + 3
   super().PopupMenu(self.GetMenu(), wx.Point(x, y))

   # After
   super().PopupMenu(self.GetMenu())
   ```
   Result: Menu still appears at far left.

2. **Position at (0, height)** - Explicit position below control:
   ```python
   height = self.GetSize().GetHeight()
   super().PopupMenu(self.GetMenu(), wx.Point(0, height))
   ```
   Result: Menu still appears at far left.

## Code Location

- `taskcoachlib/widgets/searchctrl.py` - SearchCtrl.PopupMenu() method

## Test Script

Run the test script to verify behavior on your system:

```bash
python3 bugs/issue_159_test_search_dropdown.py
```

The script opens two windows:
- Regular frame (no AUI) - baseline
- AUI frame with search in toolbar, center pane, and side pane

## Related Issues

- Issue #161: wx.Choice dropdown scrollbar issue (separate problem, same environment)
