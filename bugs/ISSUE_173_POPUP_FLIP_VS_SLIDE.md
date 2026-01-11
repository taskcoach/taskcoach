# Issue #173: PopupMenu uses FLIP instead of SLIDE when near screen edge

GitHub Issue: https://github.com/taskcoach/taskcoach/issues/173

## Problem

On Wayland, popup menus fully flip to the opposite side when they would extend beyond the screen edge, instead of sliding minimally to fit. This is jarring for widget-attached menus (SearchCtrl dropdown, ComboBox, etc.) where the menu should stay visually connected to its trigger.

## Steps to Reproduce

1. Run TaskCoach on Wayland
2. Position window so the SearchCtrl is near the right screen edge
3. Click the magnifier dropdown button

**Expected**: Menu slides left slightly to fit on screen
**Actual**: Menu flips entirely to the left side of the control

## Root Cause

GTK3's `GtkMenu:anchor-hints` property controls this behavior. By default, GTK prioritizes `GDK_ANCHOR_FLIP_X` over `GDK_ANCHOR_SLIDE_X`. wxWidgets doesn't set this property, so GTK uses its FLIP-priority default.

## Workarounds Attempted (All Failed)

### 1. PyGObject Monkey-Patching

Attempted to monkey-patch `Gtk.Menu.popup_at_pointer` via gi.repository before wxPython imports:

```python
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

_original = Gtk.Menu.popup_at_pointer
def _patched(self, trigger_event=None):
    self.set_property("anchor-hints", Gdk.AnchorHints.SLIDE_X)
    return _original(self, trigger_event)
Gtk.Menu.popup_at_pointer = _patched
```

**Why it failed:** wxWidgets calls the C GTK functions directly (e.g., `gtk_menu_popup_at_pointer()` in C), not through Python's gi.repository. Python monkey-patches only affect Python calls, not the underlying C calls made by wxWidgets/wxPython.

### 2. SWIG Pointer Access

Attempted to access the underlying GtkMenu via SWIG's `.this` attribute:

**Why it failed:**
- `wx.Menu` doesn't have a `GetHandle()` method like `wx.Window` does
- The internal GtkMenu pointer isn't exposed through any wxPython API
- Even if we could get the pointer, bridging it to gi.repository's GObject system is undocumented
- This would be fragile, version-specific, and likely break on updates

### 3. Replace wx.Menu with Gtk.Menu

Attempted to create a pure Gtk.Menu with SLIDE hints and use it in place of wx.SearchCtrl's menu:

```python
from gi.repository import Gtk, Gdk
gtk_menu = Gtk.Menu()
gtk_menu.set_property("anchor-hints", Gdk.AnchorHints.SLIDE_X)
# Add menu items...
```

**Why it failed:** wx.SearchCtrl.SetMenu() requires a wx.Menu object. There's no way to substitute a Gtk.Menu for the internal popup mechanism.

### 4. dconf/GSettings Override

Investigated whether there's a system-wide dconf/gsettings key to control anchor-hints behavior.

**Why it failed:** There isn't one. The only menu-related settings are `menu-popdown-delay` and `menu-bar-popup-delay`. The anchor-hints property is set per-menu by applications, not configurable system-wide.

### 5. LD_PRELOAD Interception

Considered an LD_PRELOAD library to intercept `gtk_menu_popup_at_pointer()` at the C level.

**Why it's not viable:** This would require writing a C shared library, is complex, platform-specific, and fragile - not recommended for a desktop application.

## Status

Waiting for upstream fix. Possible solutions:

1. wxWidgets sets `anchor-hints` to `GDK_ANCHOR_SLIDE_X` for PopupMenu/SearchCtrl
2. wxWidgets exposes the `anchor-hints` property, and wxPython makes it available to Python applications

There is no Python-level workaround.

## References

- [GTK3 anchor-hints](https://docs.gtk.org/gtk3/property.Menu.anchor-hints.html)
- [Gdk.AnchorHints](https://docs.gtk.org/gdk3/flags.AnchorHints.html)
