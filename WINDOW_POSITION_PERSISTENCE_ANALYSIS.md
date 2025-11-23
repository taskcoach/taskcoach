# Window Position Persistence Analysis

## Executive Summary

Task Coach on Linux/GTK fails to restore window position on startup. The window always appears at the window manager's "smart placement" origin instead of the saved position.

**Root Cause:** wxWidgets/wxGTK does not set the `GDK_HINT_USER_POS` geometry hint when calling `gtk_window_move()`. Without this hint, the window manager ignores application-requested positions.

**Working Solution:** Correct position/size on `EVT_MOVE`/`EVT_SIZE` until window is **ready** (activated AND position/size achieved). Then maximize if desired (fire and forget).

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
ready: bool      # Position/size achieved (NOT maximized)
activated: bool  # EVT_ACTIVATE has fired
```

### Rules

1. **Startup errors** (geometry invalid, iconized, maximized unexpectedly) → **clear state**
   - Errors repeat until general rule marks ready
   - This is by design - exceptional cases need investigation

2. **Mark ready when:** `activated` AND (`state empty` OR `position/size achieved`)
   - Ready is for position/size only, NOT maximized

3. **After ready:** ONE maximize attempt if `state.maximized=True` (fire and forget)

4. **Caching (after ready):**
   - Always: `maximized = IsMaximized()` (query window directly)
   - Only if normal state (not maximized, not iconized): cache position/size

5. **State empty** → nothing to correct, WM decides, normal caching captures values

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

### 2. `check_and_correct()` - While Not Ready

```
Called on EVT_MOVE, EVT_SIZE, EVT_MAXIMIZE, EVT_ACTIVATE

If ready: return

If iconized:
    ERROR - log and clear state
    return (will repeat until general rule marks ready)

If maximized (unexpectedly):
    ERROR - log and clear state
    return (will repeat until general rule marks ready)

If state empty:
    Mark ready when activated
else:
    Correct position if wrong
    Correct size if wrong
    Mark ready when activated AND position/size OK
```

### 3. `_mark_ready()` - Position/Size Done

```
Set ready = True
Cache final position/size from window
Stop position logging

If state.maximized:
    Call Maximize() once (fire and forget)
```

### 4. After Ready - Normal Caching

```
On EVT_MOVE, EVT_SIZE, EVT_MAXIMIZE:
    maximized = IsMaximized()  # Always query window

    If normal state (not maximized, not iconized):
        Cache position from window
        Cache size from window (if reasonable)
```

### 5. `save()` - On Close

```
Write state (position, size, maximized) to settings file
```

---

## Key Points

1. **State = Desired State**: position, size, maximized represent what we want the window to be
2. **Ready = Position/Size Only**: ready flag indicates position/size achieved, maximized is separate
3. **Maximize After Ready**: ONE attempt to maximize after position/size done (fire and forget)
4. **While Maximized**: WM manages the window, we don't attempt move/resize
5. **Caching**: Query `IsMaximized()` directly, only cache position/size in normal state
6. **Errors Clear State**: All startup errors clear state, let WM decide, normal caching captures values
7. **Errors Repeat**: Startup errors repeat until ready, highlighting exceptional cases

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
6. We keep correcting until activated AND position/size match
7. Then we mark ready and do ONE maximize attempt if needed

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
        self.ready = False      # Position/size achieved
        self.activated = False  # EVT_ACTIVATE fired

        self.load()  # Load from settings

        # Bind events
        window.Bind(wx.EVT_MOVE, self._on_move)
        window.Bind(wx.EVT_SIZE, self._on_size)
        window.Bind(wx.EVT_MAXIMIZE, self._on_maximize)
        window.Bind(wx.EVT_ACTIVATE, self._on_activate)

    def check_and_correct(self):
        """Try to achieve desired state. Called while not ready."""
        if self.ready:
            return

        state_empty = self.position is None and self.size is None

        # Startup errors - clear state
        if self._window.IsIconized():
            self._clear_state()
            return

        if self._window.IsMaximized():
            self._clear_state()
            return

        # Correct position/size
        position_size_achieved = False
        if not state_empty:
            pos_ok = self._check_position()
            size_ok = self._check_size()
            position_size_achieved = pos_ok and size_ok

        # Mark ready when: activated AND (empty OR achieved)
        if self.activated and (state_empty or position_size_achieved):
            self._mark_ready()

    def _mark_ready(self):
        """Position/size done. Maximize if needed (fire and forget)."""
        self.ready = True

        # Cache final values
        pos = self._window.GetPosition()
        size = self._window.GetSize()
        self.position = (pos.x, pos.y)
        self.size = (size.width, size.height)

        # ONE maximize attempt
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
```

---

## Platform Considerations

### Linux/GTK (X11)
- EVT_MOVE/EVT_SIZE detection needed
- Window manager may move window multiple times before ready
- Correct position/size until activated AND achieved

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
2. ✅ Startup errors clear state, let WM decide
3. ✅ Ready = activated AND (empty OR position/size achieved)
4. ✅ After ready: ONE maximize attempt (fire and forget)
5. ✅ Caching: query IsMaximized(), only cache position/size in normal state
6. ✅ Geometry validation: position on screen, size fits monitor
7. ✅ Wayland detection: logs warning

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
