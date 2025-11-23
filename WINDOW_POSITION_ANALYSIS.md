# Window Position Persistence Problem Analysis

## Executive Summary

Task Coach on Linux/GTK fails to restore window position on startup. The window always appears at the window manager's "smart placement" origin (80, 0 with left taskbar) instead of the saved position.

**Root Cause:** wxWidgets/wxGTK does not set the `GDK_HINT_USER_POS` geometry hint when calling `gtk_window_move()`. Without this hint, the window manager ignores application-requested positions and uses its own placement algorithm.

**Working Solution:** Detect unplanned window moves via `EVT_MOVE` and immediately reset to the target position. This works without visible flicker.

---

## Problem Description

### Symptoms
- Window position is saved correctly on close
- On restart, window appears at (80, 0) instead of saved position
- Position (80, 0) is the top-left of usable screen area (accounting for 80px left taskbar)
- Visible "flicker" when using delayed position correction

### Environment
- Platform: Linux (X11)
- GUI Toolkit: wxPython 4.x with GTK3 backend
- Window Manager: Various (Openbox, Mutter, KWin, etc.)

---

## Technical Analysis

### How GTK Window Positioning Works

1. **Window Manager Control**: On X11/GTK, the window manager (WM) controls window placement
2. **Smart Placement**: WMs use algorithms like "smart placement" to position new windows
3. **Position Hints**: Applications can request specific positions via X11 hints:
   - `PPosition` - Program-specified position
   - `USPosition` - User-specified position (WM should honor this)
4. **GDK_HINT_USER_POS**: GTK flag that sets `USPosition` hint, telling WM to honor the position

### What Pure GTK Does (Working)

```python
# This works - window appears at (100, 100)
geometry = Gdk.Geometry()
window.set_geometry_hints(None, geometry, Gdk.WindowHints.USER_POS)
window.move(100, 100)
window.show_all()
```

The `USER_POS` hint tells the WM: "User explicitly requested this position, please honor it."

### What wxWidgets/wxGTK Does (Broken)

From `wxWidgets/src/gtk/toplevel.cpp`:

```cpp
// wxGTK calls gtk_window_move() but does NOT set GDK_HINT_USER_POS
if (m_x != old_x || m_y != old_y)
{
    gtk_window_move(GTK_WINDOW(m_widget), m_x, m_y);
}
```

wxGTK only sets these geometry hints:
- `GDK_HINT_MIN_SIZE`
- `GDK_HINT_MAX_SIZE`
- `GDK_HINT_RESIZE_INC`

**Missing:** `GDK_HINT_USER_POS` - This is why the WM ignores wxPython's position requests.

### The Race Condition

When wxPython shows a window:

1. wxGTK calls `gtk_window_move(m_x, m_y)` - position set to (100, 100)
2. Window is mapped/shown
3. WM receives map request WITHOUT `USPosition` hint
4. WM applies "smart placement" → moves window to (80, 0)
5. Application receives `EVT_MOVE` with (80, 0)

---

## Test Results Summary

### Pure GTK Tests (Working)

| Test | Method | Result |
|------|--------|--------|
| `test_gtk_geometry_hints.py` | `set_geometry_hints(USER_POS)` before show | ✓ Works, no flicker |
| `test_gdk_user_position.py` | `gdk_window.move()` on realize | ✓ Works, no flicker |

### wxPython Standard Approaches (All Fail)

| Test | Method | Result |
|------|--------|--------|
| `test_wx_pos_constructor.py` | `pos=` in constructor | ✗ WM ignores |
| `test_wx_pos_before_show.py` | `SetPosition()` before Show | ✗ WM ignores |
| `test_wx_pos_after_show.py` | `SetPosition()` after Show | ✗ WM ignores |
| `test_wx_pos_callafter.py` | `wx.CallAfter(SetPosition)` | ✗ WM ignores |
| `test_wx_pos_move.py` | `Move()` before Show | ✗ WM ignores |
| `test_wx_pos_evt_idle.py` | `EVT_IDLE` handler | ✗ Race condition |

### wxPython + GTK Hint Attempts (All Fail)

| Test | Method | Result |
|------|--------|--------|
| `test_wx_like_gtk.py` | Find GtkWindow + USER_POS | ✗ WM overrides after |
| `test_wx_gtk_hint_early.py` | GTK hint before Show | ✗ Goes to 100,100 then 80,0 |
| `test_wx_gtk_hint_after_show.py` | GTK hint after Show | ✗ Goes to 100,100 then 80,0 |
| `test_wx_internal_pos.py` | wx pos + GTK hint | ✗ Goes to 80,0 |
| `test_wx_window_create.py` | EVT_WINDOW_CREATE + from_address | ✗ from_address API doesn't exist |
| `test_wx_gobject_wrap.py` | GObject.GObject(handle) | ✗ GObject() takes 0 args |
| `test_wx_xid_lookup.py` | XID → GdkWindow.move() | ✗ move() works but no USER_POS hint |

### wxPython Working Solutions

| Test | Method | Result | Flicker? |
|------|--------|--------|----------|
| `test_wx_pos_calllater.py` | `CallLater(50ms)` | ✓ Works | Yes |
| **`test_wx_pos_unplanned_move.py`** | **EVT_MOVE detect + reset** | **✓ Works** | **No** |

---

## Why GTK Hints Don't Work from wxPython

### Problem 1: GetHandle() Returns XID, Not GtkWidget

```python
handle = frame.GetHandle()  # Returns X11 window ID (XID), NOT GtkWidget pointer
```

From [wxWidgets/Phoenix issue #1217](https://github.com/wxWidgets/Phoenix/issues/1217):
> "GetHandle docs say this returns a GtkHandle on GTK, but the current code is returning e.g. an XID on X11"

### Problem 2: wxGTK Overrides GTK Hints

Even when we successfully set GTK hints via `Gtk.Window.list_toplevels()`:

1. Our hint sets position to (100, 100) ✓
2. wxGTK's `Show()` calls `gtk_window_move(m_x, m_y)`
3. This call does NOT preserve our `USER_POS` hint
4. WM sees the move request without `USPosition` → ignores it

### Problem 3: EVT_WINDOW_CREATE Timing

`EVT_WINDOW_CREATE` fires **AFTER** `Show()`, not before:

```
Before Show: (0, 0)
After Show: (0, 0)
EVT_WINDOW_CREATE fired    ← Too late!
EVT_MOVE #1: (994, 0)
```

This means we cannot set GTK hints before the window is mapped.

### Problem 4: GdkWindow.move() Doesn't Set Hint

Even when we successfully get the GdkWindow and call `move()`:

```python
gdk_window = GdkX11.X11Window.foreign_new_for_display(display, xid)
gdk_window.move(100, 100)  # Called successfully
# But window still goes to (994, 0)!
```

`GdkWindow.move()` does NOT set `USER_POS` hint - only `GtkWindow.set_geometry_hints()` does.

### Problem 5: Timing of WM Events

The monitor test (`test_wx_gtk_monitor.py`) revealed the sequence:

```
wx EVT_MOVE #1: (100, 100)     ← Our position initially works
GTK configure-event: (2, 25)   ← Client area position
wx EVT_SIZE: (6, 28)           ← wxGTK internal sizing
GTK map: (root_x=-2, root_y=-25) ← Strange coordinates
wx EVT_SHOW
wx EVT_MOVE #2: (80, 0)        ← WM repositions!
```

wxGTK's internal sizing/mapping process triggers the WM to reposition the window.

---

## Working Solution: EVT_MOVE Detection

### Implementation

```python
class MainWindow(wx.Frame):
    def __init__(self):
        super().__init__(None, title="App", size=(800, 600))
        self._target_position = (100, 100)  # Loaded from settings
        self._position_applied = False

        # Set initial position hint via 4-param SetSize
        self.SetSize(self._target_position[0], self._target_position[1], 800, 600)

        self.Bind(wx.EVT_MOVE, self._on_move)

    def _on_move(self, event):
        pos = event.GetPosition()

        # Detect unplanned move (WM placement)
        if not self._position_applied:
            if pos.x != self._target_position[0] or pos.y != self._target_position[1]:
                # WM moved us - immediately correct
                self._position_applied = True
                self.SetPosition(wx.Point(*self._target_position))

        event.Skip()
```

### Why This Works

1. 4-param `SetSize()` provides a position "hint" to GTK
2. Window initially appears at target position briefly
3. WM moves window to (80, 0) - triggers `EVT_MOVE`
4. We detect unplanned move and immediately call `SetPosition()`
5. After window is shown, `SetPosition()` is honored by WM
6. Correction happens fast enough that user doesn't see flicker

### Platform Considerations

```python
import sys

if sys.platform == 'linux':
    # Use EVT_MOVE detection for GTK/Linux
    self.Bind(wx.EVT_MOVE, self._on_move)
elif sys.platform == 'darwin':
    # macOS: Standard positioning works
    self.SetPosition(target)
elif sys.platform == 'win32':
    # Windows: Standard positioning works
    self.SetPosition(target)
```

### Wayland Caveat

On Wayland, window positioning is **disabled by design**:
- `GetPosition()` always returns (0, 0)
- `SetPosition()` has no effect
- No workaround exists

---

## Recommendations

### For Task Coach

1. **Implement EVT_MOVE detection** in `windowdimensionstracker.py`
2. Use 4-param `SetSize(x, y, w, h)` to provide initial position hint
3. Detect unplanned moves and immediately correct
4. Add platform detection for Wayland (disable position restore)

### For wxWidgets Project

File a feature request to add `GDK_HINT_USER_POS` support:
- When `SetPosition()` is called, set the hint
- Or add a new method `SetUserPosition()` that explicitly sets the hint

---

## References

- [wxWidgets/Phoenix Issue #2214](https://github.com/wxWidgets/Phoenix/issues/2214) - Frame position problem on Linux
- [wxWidgets/Phoenix Issue #1217](https://github.com/wxWidgets/Phoenix/issues/1217) - GetHandle() returns XID
- [GTK gtk_window_move() docs](https://docs.gtk.org/gtk3/method.Window.move.html) - WM ignores initial positions
- [Gdk.WindowHints](https://docs.gtk.org/gdk3/flags.WindowHints.html) - USER_POS hint
- [wxWidgets src/gtk/toplevel.cpp](https://github.com/wxWidgets/wxWidgets/blob/master/src/gtk/toplevel.cpp) - wxGTK implementation

---

## Test Files

All test files are in the repository root:

```
test_gtk_geometry_hints.py      # Pure GTK - works
test_gdk_user_position.py       # Pure GTK - works
test_wx_pos_constructor.py      # wx pos in constructor - fails
test_wx_pos_before_show.py      # wx SetPosition before Show - fails
test_wx_pos_after_show.py       # wx SetPosition after Show - fails
test_wx_pos_callafter.py        # wx CallAfter - fails
test_wx_pos_calllater.py        # wx CallLater 50ms - works with flicker
test_wx_pos_move.py             # wx Move() - fails
test_wx_pos_evt_idle.py         # wx EVT_IDLE - fails (race condition)
test_wx_pos_unplanned_move.py   # wx EVT_MOVE detect - WORKS, NO FLICKER
test_wx_like_gtk.py             # wx + GTK hint via toplevels - fails
test_wx_gtk_hint_early.py       # GTK hint before Show - fails
test_wx_gtk_hint_after_show.py  # GTK hint after Show - fails
test_wx_gtk_monitor.py          # GTK event monitor - diagnostic
test_wx_internal_pos.py         # wx internal + GTK hint - fails
test_wx_window_create.py        # EVT_WINDOW_CREATE - API error
test_wx_gobject_wrap.py         # GObject wrap - wrong pointer type
test_wx_xid_lookup.py           # XID lookup - needs testing
```

---

*Document created: 2025-11-23*
*Last updated: 2025-11-23*
