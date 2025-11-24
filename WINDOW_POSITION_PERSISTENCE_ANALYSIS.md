# Window Position Persistence Analysis

## Executive Summary

Task Coach on Linux/GTK fails to restore window position on startup. The window always appears at the window manager's "smart placement" origin instead of the saved position.

**Root Cause:** wxWidgets/wxGTK does not set the `GDK_HINT_USER_POS` geometry hint when calling `gtk_window_move()`. Without this hint, the window manager ignores application-requested positions.

**Working Solution:** Correct position/size on `EVT_MOVE`/`EVT_SIZE` until window is **ready** (active, confirmed, and achieved). Then maximize if desired (fire and forget).

---

## State Model

### State (Desired State, Persisted)

```python
position: (x, y) or None    # Desired restore position
size: (w, h) or None        # Desired restore size
maximized: bool             # Desired maximize state
```

### In-Memory State

```python
ready: bool               # Position/size achieved
position_confirmed: bool  # SetPosition() result confirmed by EVT_MOVE (starts True)
size_confirmed: bool      # SetSize() result confirmed by EVT_SIZE (starts True)
```

### Rules

1. **Startup errors** (geometry invalid, iconized, maximized unexpectedly) → **clear state**
   - Errors repeat until general rule marks ready
   - This is by design - exceptional cases need investigation

2. **On mismatch:** set respective `confirmed=False`, send correction (SetPosition/SetSize)

3. **On EVT_MOVE:** `position_confirmed = True`

4. **On EVT_SIZE:** `size_confirmed = True`

5. **Mark ready when (on EVT_IDLE):** `IsActive()` AND `position_confirmed` AND `size_confirmed` AND (`state empty` OR `position/size achieved`)
   - Ready is for position/size only, NOT maximized
   - Using EVT_IDLE ensures GTK has fully processed geometry changes

6. **After ready:** ONE maximize attempt if `state.maximized=True` (fire and forget)
   - This ensures the restore geometry is properly stored before maximizing

7. **Caching (after ready):**
   - Always: `maximized = IsMaximized()` (query window directly)
   - Only if normal state (not maximized, not iconized): cache position/size

8. **State empty** → nothing to correct, WM decides, normal caching captures values

---

## Flow

### 1. `load()` - Startup

```
Read position, size, maximized from settings file
Validate geometry (position on screen, size fits monitor)
├── Valid: set state (position, size, maximized)
└── Invalid: clear state (position=None, size=None, maximized=False)
    - Let WM place window
    - Normal caching will capture values
```

### 2. `check_and_correct()` - On EVT_MOVE/EVT_SIZE

```
If ready: return

If iconized:
    ERROR - log and clear state
    return (will repeat until ready)

If maximized (unexpectedly):
    ERROR - log and clear state
    return (will repeat until ready)

If state not empty:
    If position wrong: position_confirmed=False, SetPosition()
    If size wrong: size_confirmed=False, SetSize()
```

### 3. `_on_move()` / `_on_size()` - Event Handlers

```
_on_move:
    position_confirmed = True
    check_and_correct()

_on_size:
    size_confirmed = True
    check_and_correct()
```

### 4. `_on_idle()` - Check Ready Conditions

```
If ready: return

If not IsActive(): return
If not position_confirmed: return
If not size_confirmed: return
If iconized or maximized: return

If state empty OR position/size achieved:
    _mark_ready()
```

### 5. `_mark_ready()` - Position/Size Done

```
Set ready = True
Cache final position/size from window
Stop position logging

If state.maximized:
    Call Maximize() once (fire and forget)
```

### 6. After Ready - Normal Caching

```
On EVT_MOVE, EVT_SIZE, EVT_MAXIMIZE:
    maximized = IsMaximized()  # Always query window

    If normal state (not maximized, not iconized):
        Cache position from window
        Cache size from window (if reasonable)
```

### 7. `save()` - On Close

```
Write state (position, size, maximized) to settings file
```

---

## Key Points

1. **State = Desired State**: position, size, maximized represent what we want the window to be
2. **Ready = Position/Size Only**: ready flag indicates position/size achieved, maximized is separate
3. **Confirmed Flags**: Track that SetPosition/SetSize results have been received via events
4. **EVT_IDLE for Ready**: Only mark ready during idle to ensure GTK has processed geometry
5. **Maximize After Ready**: ONE attempt to maximize after position/size done (fire and forget)
6. **Restore Geometry**: By waiting for EVT_IDLE before maximize, GTK stores correct restore geometry
7. **While Maximized**: WM manages the window, we don't attempt move/resize
8. **Caching**: Query `IsMaximized()` directly, only cache position/size in normal state
9. **Errors Clear State**: All startup errors clear state, let WM decide, normal caching captures values
10. **Errors Repeat**: Startup errors repeat until ready, highlighting exceptional cases

---

## Problem Description

### Symptoms
- Window position is saved correctly on close
- On restart, window appears at WM's default position instead of saved position
- Position is typically upper-left of usable screen area

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

### What wxWidgets/wxGTK Does (Broken)

wxGTK calls `gtk_window_move()` but does NOT set `GDK_HINT_USER_POS`. Without this hint, the WM ignores application-requested positions.

### Why Our Solution Works

1. We set initial position/size via `SetSize(x, y, w, h)`
2. GTK/WM ignores this and applies "smart placement"
3. We detect wrong position/size via `EVT_MOVE`/`EVT_SIZE`
4. We correct by calling `SetPosition()`/`SetSize()` again
5. After window is mapped and visible, these calls ARE honored
6. We track corrections via confirmed flags
7. On EVT_IDLE, when active and all confirmed, we mark ready
8. Then we do ONE maximize attempt if needed (with correct restore geometry)

### Why Confirmed Flags and EVT_IDLE

The maximize problem: When `Maximize()` is called immediately after `SetPosition()`/`SetSize()`, GTK hasn't finished internally storing the "restore geometry". The maximize captures a stale restore size.

Solution:
- Track that our SetPosition/SetSize corrections have been confirmed by receiving EVT_MOVE/EVT_SIZE
- Only mark ready during EVT_IDLE, ensuring the event loop has processed all pending geometry changes
- Then maximize - GTK now has the correct restore geometry stored

---

## Implementation

```python
class WindowGeometryTracker:
    """Track and restore window geometry (position, size, maximized state).

    State = desired state. While not ready, keep trying to achieve it.
    """

    def __init__(self, window, settings, section):
        # Desired state (persisted)
        self.position = None    # (x, y)
        self.size = None        # (w, h)
        self.maximized = False

        # In-memory state
        self.ready = False              # Position/size achieved
        self.position_confirmed = True  # No pending SetPosition()
        self.size_confirmed = True      # No pending SetSize()

        self.load()  # Load from settings

        # Bind events
        window.Bind(wx.EVT_MOVE, self._on_move)
        window.Bind(wx.EVT_SIZE, self._on_size)
        window.Bind(wx.EVT_MAXIMIZE, self._on_maximize)
        window.Bind(wx.EVT_IDLE, self._on_idle)

    def check_and_correct(self):
        """Try to achieve desired state. Called on EVT_MOVE/EVT_SIZE."""
        if self.ready:
            return

        # Startup errors - clear state
        if self._window.IsIconized() or self._window.IsMaximized():
            self._clear_state()
            return

        # Correct position/size, setting confirmed=False
        if self.position is not None or self.size is not None:
            self._check_position()  # Sets position_confirmed=False if correcting
            self._check_size()      # Sets size_confirmed=False if correcting

    def _on_move(self, event):
        self.position_confirmed = True
        self.check_and_correct()
        event.Skip()

    def _on_size(self, event):
        self.size_confirmed = True
        self.check_and_correct()
        event.Skip()

    def _on_idle(self, event):
        """Check ready conditions. Only mark ready during idle."""
        if self.ready:
            event.Skip()
            return

        # All conditions must be met
        if not self._window.IsActive():
            event.Skip()
            return
        if not self.position_confirmed or not self.size_confirmed:
            event.Skip()
            return
        if self._window.IsIconized() or self._window.IsMaximized():
            event.Skip()
            return

        # Check if state empty or achieved
        state_empty = self.position is None and self.size is None
        if state_empty or self._position_size_achieved():
            self._mark_ready()

        event.Skip()

    def _mark_ready(self):
        """Position/size done. Maximize if needed (fire and forget)."""
        self.ready = True

        # Cache final values
        pos = self._window.GetPosition()
        size = self._window.GetSize()
        self.position = (pos.x, pos.y)
        self.size = (size.width, size.height)

        # ONE maximize attempt - GTK now has correct restore geometry
        if self.maximized:
            self._window.Maximize()

    def cache_from_window(self):
        """Update state from window. Called after ready."""
        self.maximized = self._window.IsMaximized()

        if self._is_normal_state():
            pos = self._window.GetPosition()
            size = self._window.GetSize()
            self.position = (pos.x, pos.y)
            self.size = (size.width, size.height)

    def _clear_state(self):
        """Clear state - WM decides, normal caching captures values."""
        self.position = None
        self.size = None
        self.maximized = False
        self.position_confirmed = True
        self.size_confirmed = True
```

---

## Dialog Windows (Subwindows)

Dialogs have special positioning rules to ensure they stay with their parent.

### State (Persisted)

```python
position: (x, y) or (-1, -1)  # (-1, -1) = no saved position
size: (w, h) or (-1, -1)      # (-1, -1) = let system decide
# NEVER save/use maximized or iconized for dialogs
```

### Rules (in order)

1. **Always on parent's monitor** - Dialog appears on same monitor as parent
2. **Missing size OR position** (-1 value) → let system decide both, clear cache
3. **Size too big for monitor** → clear all cache, let system decide
4. **Position off-screen (but size OK)** → keep size, center on parent, clear position cache
5. **Valid size and position** → use saved values

### Flow

```
load():
    1. Get parent's current monitor work_area

    2. If saved size OR position is missing (-1):
        → Clear geometry cache
        → Let system choose defaults

    3. If saved size > work_area:
        → Clear geometry cache
        → Let system choose defaults

    4. If saved position off-screen:
        → Keep saved size (it fits)
        → Center on parent
        → Clear position cache only

    5. Otherwise:
        → Use saved size and position
```

### Implementation

```python
def _load_dialog_geometry(self, x, y, width, height, min_w, min_h):
    """Load geometry for dialog (must be on same monitor as parent)."""
    parent_display_idx = self._get_parent_display_index()
    work_area = wx.Display(parent_display_idx).GetClientArea()

    # Rule 2: Missing geometry → let system decide
    if x == -1 or y == -1 or width == -1 or height == -1:
        self._clear_dialog_cache()
        return

    # Rule 3: Size too big → clear cache, let system decide
    if width > work_area.width or height > work_area.height:
        self._clear_dialog_cache()
        return

    # Rule 4: Position off-screen → keep size, center, clear position
    if not self._is_position_on_screen(x, y, width, height, work_area):
        self._center_on_parent_with_size(width, height)
        self._clear_position_cache()
        return

    # Rule 5: Valid → use saved values
    self.position = (x, y)
    self.size = (width, height)
    self._window.SetSize(x, y, width, height)
```

### Usage

```python
# For dialogs - pass parent window
WindowGeometryTracker(dialog, settings, section, parent=main_window)

# For main window - no parent
WindowGeometryTracker(main_window, settings, section)
```

---

## Platform Considerations

### Linux/GTK (X11)
- EVT_MOVE/EVT_SIZE detection needed
- Window manager may move window multiple times before ready
- Correct position/size until active, confirmed, and achieved
- Wait for EVT_IDLE before maximize to ensure correct restore geometry

### Windows/macOS
- Standard positioning works
- No correction needed

### Wayland
- Window positioning disabled by design
- `GetPosition()` always returns (0, 0)
- `SetPosition()` has no effect
- No workaround exists - log warning

---

## Recommendations

### For Task Coach (Implemented)

1. ✅ State model: position, size, maximized as desired state
2. ✅ Confirmed flags: position_confirmed, size_confirmed
3. ✅ On mismatch: set confirmed=False, send correction
4. ✅ On EVT_MOVE/EVT_SIZE: set respective confirmed=True
5. ✅ On EVT_IDLE: check ready conditions
6. ✅ Ready = IsActive() AND confirmed AND (empty OR achieved)
7. ✅ After ready: ONE maximize attempt (fire and forget)
8. ✅ Caching: query IsMaximized(), only cache position/size in normal state
9. ✅ Geometry validation: position on screen, size fits monitor
10. ✅ Wayland detection: logs warning
11. ✅ Dialog positioning: constrained to parent's monitor, centered if invalid

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

---

*Document created: 2025-11-23*
*Last updated: 2025-11-23*
