# Issue #159: Search Dropdown Shows at Far Left of Pane

GitHub Issue: https://github.com/taskcoach/taskcoach/issues/159

## Problem

On Wayland, clicking the search control's magnifier dropdown button causes the menu to appear at the far left of the AUI pane instead of directly below the search control.

## Environment

- Kubuntu 24 with KDE Plasma + Wayland
- wxPython 4.2.1 gtk3 (phoenix) wxWidgets 3.2.4

## Root Cause

Wayland does not support global coordinates. Popup menus must be positioned relative to their transient parent window. When `PopupMenu()` is called on a widget nested inside containers (panels, sizers with spacers), the transient parent relationship is established incorrectly, causing coordinates to be relative to a parent container rather than the widget itself.

From [KDE Wayland Porting Notes](https://community.kde.org/Guidelines_and_HOWTOs/Wayland_Porting_Notes):
> "Popup menus will be misplaced on Wayland because the compositor needs to know how to relate the menu's window with the main window of the application."

## Solution

Wrap the SearchCtrl in a tight-fitting container panel and call `PopupMenu()` on the container:

```python
class SearchCtrlContainer(wx.Panel):
    """SearchCtrl in tight-fitting panel for correct popup positioning on Wayland."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.search = wx.SearchCtrl(self, size=kwargs.get('size', (200, -1)))
        # ... setup menu ...
        sizer.Add(self.search, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.search.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, self._on_menu_btn)

    def _on_menu_btn(self, event):
        menu = self.search.GetMenu()
        if menu:
            height = self.GetSize().GetHeight()
            self.PopupMenu(menu, wx.Point(0, height))
```

**Why this works:**
1. Container fits SearchCtrl exactly, so (0,0) of container = (0,0) of SearchCtrl
2. `container.PopupMenu(menu, (0, height))` establishes correct transient parent
3. Coordinates are now relative to the container origin, which aligns with the SearchCtrl

## Code Location

- `taskcoachlib/widgets/searchctrl.py` - SearchCtrl.PopupMenu() method

## Test Script

```bash
python3 bugs/issue_159_test_search_dropdown.py
```

The "Tight container (0,h)" test demonstrates the working solution.

## References

- [KDE Wayland Porting Notes](https://community.kde.org/Guidelines_and_HOWTOs/Wayland_Porting_Notes) - transient parent requirements
- [gtk_menu_popup_at_widget](https://docs.gtk.org/gtk3/method.Menu.popup_at_widget.html) - GTK3 popup positioning
- [wxWidgets Issue #22328](https://github.com/wxWidgets/wxWidgets/issues/22328) - gtk_menu_popup deprecation
