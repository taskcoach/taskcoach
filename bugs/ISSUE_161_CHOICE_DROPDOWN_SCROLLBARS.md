# Issue #161: wx.Choice Dropdown Shows Mini-Scrollbars on KDE Wayland

GitHub Issue: https://github.com/taskcoach/taskcoach/issues/161

## Problem

On KDE Plasma with Wayland, all `wx.Choice` dropdown controls display unwanted mini-scrollbars, even when there are only 2 items in the list.

## Test Results

Tested on Kubuntu 24 with KDE Plasma + Wayland using `bugs/issue_161_test_choice_dropdown.py`:

- **wx.Choice**: ALL variations show scrollbar issue
- **wx.ComboBox**: Does NOT have this issue

The issue affects all wx.Choice controls regardless of:
- Number of items
- Sizing method (SetMinSize, SetSize, sizer flags)
- Parent container (panel, toolbar, dialog)

## Related Issues

- [Mozilla Bug #1718507](https://bugzilla.mozilla.org/show_bug.cgi?id=1718507): [Wayland/KDE] Popup menus are small
- [wxWidgets GitHub #24473](https://github.com/wxWidgets/wxWidgets/issues/24473): Dropdowns showing half screen away on Wayland
- [wxWidgets Forum](https://forums.wxwidgets.org/viewtopic.php?f=23&t=52389): wxDataViewChoiceRenderer visual bug on KDE+Wayland

## Test Script

Run the test script to verify behavior on your system:

```bash
python3 bugs/issue_161_test_choice_dropdown.py
```

The script tests wx.Choice and wx.ComboBox in various configurations.
