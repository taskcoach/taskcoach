# Issue #159: Search Dropdown Shows at Far Left of Pane

GitHub Issue: https://github.com/taskcoach/taskcoach/issues/159

## Problem

On Wayland, clicking the search control's magnifier dropdown button causes the menu to appear at the far left of the AUI pane instead of directly below the search control.

## Environment

- Kubuntu 24 with KDE Plasma + Wayland
- wxPython 4.2.1 gtk3 (phoenix) wxWidgets 3.2.4

## Root Cause

Wayland does not support global coordinates. Popup menus are positioned by the Wayland compositor relative to a **transient parent window**. When `PopupMenu()` is called on a widget nested inside containers (toolbars, panels with sizers/spacers), Wayland may use the wrong ancestor as the transient parent, causing the popup to appear misaligned.

From [KDE Wayland Porting Notes](https://community.kde.org/Guidelines_and_HOWTOs/Wayland_Porting_Notes):
> "Popup menus will be misplaced on Wayland because the compositor needs to know how to relate the menu's window with the main window of the application."

## What is a Transient Parent?

On Wayland, every popup window must declare which window it belongs to (its "transient parent"). The compositor positions the popup relative to this parent. Unlike X11, there are no global screen coordinates - the compositor handles all positioning.

When you call `widget.PopupMenu(menu)`, wxWidgets/GTK tells Wayland "this popup belongs to `widget`". If `widget` is deeply nested in a container hierarchy, Wayland may not establish the relationship correctly.

## Solution: Wrap in a Tight-Fitting Panel

Wrap the SearchCtrl in a `wx.Panel` that fits exactly around it. Call `PopupMenu()` on this Panel wrapper:

```python
class SearchCtrl(wx.Panel):
    """SearchCtrl wrapped in tight-fitting Panel for Wayland compatibility."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._inner = wx.SearchCtrl(self, ...)
        sizer.Add(self._inner, 0, wx.EXPAND)
        self.SetSizer(sizer)
        self._inner.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self._on_menu_btn)

    def _on_menu_btn(self, event):
        menu = self._inner.GetMenu()
        if menu:
            self.PopupMenu(menu)  # Position argument is optional
```

**Why this works:**
1. The Panel is a distinct window that fits tightly around the SearchCtrl
2. Calling `panel.PopupMenu(menu)` establishes the Panel as the transient parent
3. Wayland positions the popup relative to the Panel, which aligns with the SearchCtrl
4. **Position coordinates are irrelevant** - the compositor handles placement

**Key insight:** The position argument to `PopupMenu()` doesn't matter on Wayland. What matters is WHICH window you call `PopupMenu()` on. That window becomes the transient parent.

## Code Location

- `taskcoachlib/widgets/searchctrl.py` - SearchCtrl is now a `wx.Panel` wrapping `_SearchCtrlInner`

## Test Script

```bash
python3 bugs/issue_159_test_search_dropdown.py
```

Tests confirm: All Panel wrapper variants work (with or without position), all non-Panel approaches fail.

## Known Limitation

When the search box is near the screen edge, the popup menu may flip to the opposite side instead of sliding minimally to fit. See [Issue #173](https://github.com/taskcoach/taskcoach/issues/173) for details.

## References

- [KDE Wayland Porting Notes](https://community.kde.org/Guidelines_and_HOWTOs/Wayland_Porting_Notes) - transient parent requirements
- [gtk_menu_popup_at_widget](https://docs.gtk.org/gtk3/method.Menu.popup_at_widget.html) - GTK3 popup positioning
- [wxWidgets Issue #22328](https://github.com/wxWidgets/wxWidgets/issues/22328) - gtk_menu_popup deprecation
