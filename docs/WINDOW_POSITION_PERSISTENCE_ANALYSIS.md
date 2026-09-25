# Window Position Persistence Analysis

## Executive Summary

Task Coach on Linux/GTK fails to restore window position on startup. The window always appears at the window manager's "smart placement" origin instead of the saved position.

**Root Cause:** wxWidgets/wxGTK does not set the `GDK_HINT_USER_POS` geometry hint when calling `gtk_window_move()`. Without this hint, the window manager ignores application-requested positions.

**Working Solution:** Correct position/size on `EVT_MOVE`/`EVT_SIZE` until window is **ready** (active, confirmed, and achieved). Then maximize if desired (fire and forget).

---

# Part 1: Main Window

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

## Rules

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

# Part 2: Dialog Windows (Subwindows)

Dialogs have **different** positioning rules than the main window. They must stay with their parent window and never support maximized/iconized states.

## State Model

### State (Persisted)

```python
position: (x, y) or (-1, -1)  # (-1, -1) = no saved position
size: (w, h) or (-1, -1)      # (-1, -1) = let system decide
# NEVER save/use maximized or iconized for dialogs
```

### Key Differences from Main Window

| Aspect | Main Window | Dialog |
|--------|-------------|--------|
| Monitor | Can be on any monitor | Must be on parent's monitor |
| Maximized | Supported | Never supported |
| Iconized | Supported | Never supported |
| No saved geometry | Let WM decide | Let system decide |
| Position invalid | Clear all state | Keep size, center on parent |

## Rules (in order)

1. **Always on parent's monitor** - Dialog appears on same monitor as parent window

2. **Missing size** (`-1` value) → let system decide both, clear cache
   - Position is meaningless without size

3. **Missing position** (but size valid) → keep size, center on parent
   - Don't clear size cache

4. **Size too big for monitor** → clear all cache, let system decide

5. **Position off-screen** (but size OK) → keep size, center on parent, clear position cache only

6. **Valid size and position** → use saved values

## Flow

```
_load_dialog_geometry():
    1. Get parent's current monitor work_area

    2. If saved size is missing (-1):
        → Clear all geometry cache
        → Let system choose defaults
        → RETURN

    3. If saved position is missing (-1) but size valid:
        → Keep saved size
        → Center on parent
        → RETURN

    4. If saved size > work_area:
        → Clear all geometry cache
        → Let system choose defaults
        → RETURN

    5. If saved position off-screen:
        → Keep saved size (it fits)
        → Center on parent
        → Clear position cache only
        → RETURN

    6. Otherwise (valid):
        → Use saved size and position
```

## Implementation

```python
def _load_dialog_geometry(self, x, y, width, height, min_w, min_h):
    """Load geometry for dialog (must be on same monitor as parent)."""
    parent_display_idx = self._get_parent_display_index()
    if parent_display_idx < 0:
        self._clear_dialog_cache()
        return

    work_area = wx.Display(parent_display_idx).GetClientArea()

    size_missing = width == -1 or height == -1
    position_missing = x == -1 or y == -1

    # Rule 2: Missing size → let system decide both
    if size_missing:
        self._clear_dialog_cache()
        return

    # Rule 3: Missing position but have size → center with saved size
    if position_missing:
        self._center_on_parent_with_size(width, height)
        return

    # Rule 4: Size too big → clear cache, let system decide
    if width > work_area.width or height > work_area.height:
        self._clear_dialog_cache()
        return

    # Rule 5: Position off-screen → keep size, center, clear position
    if not self._is_position_on_screen(x, y, width, height, work_area):
        self._center_on_parent_with_size(width, height)
        self._clear_position_cache()
        return

    # Rule 6: Valid → use saved values
    self.position = (x, y)
    self.size = (width, height)
    self._window.SetSize(x, y, width, height)
```

## Helper Methods

```python
def _is_position_on_screen(self, x, y, width, height, work_area):
    """Check if dialog is fully visible on the parent's monitor.

    Dialog must be entirely within the work area. Positions and sizes
    already include window decorations, so no tolerance is needed.
    """
    if x < work_area.x:
        return False  # Left edge off screen
    if y < work_area.y:
        return False  # Top edge off screen
    if x + width > work_area.x + work_area.width:
        return False  # Right edge off screen
    if y + height > work_area.y + work_area.height:
        return False  # Bottom edge off screen
    return True

def _center_on_parent_with_size(self, width, height):
    """Center on parent with specified size. Sets position and size state."""
    parent_pos = self._parent.GetPosition()
    parent_size = self._parent.GetSize()

    x = parent_pos.x + (parent_size.width - width) // 2
    y = parent_pos.y + (parent_size.height - height) // 2

    # Clamp to work area
    work_area = wx.Display(parent_display_idx).GetClientArea()
    x = max(work_area.x, min(x, work_area.x + work_area.width - width))
    y = max(work_area.y, min(y, work_area.y + work_area.height - height))

    self.position = (x, y)
    self.size = (width, height)
    self._window.SetSize(x, y, width, height)

def _clear_dialog_cache(self):
    """Clear dialog geometry cache in settings."""
    self._set_setting("position", (-1, -1))
    self._set_setting("size", (-1, -1))
    self.position = None
    self.size = None

def _clear_position_cache(self):
    """Clear only position cache in settings."""
    self._set_setting("position", (-1, -1))
```

## Usage

```python
# For dialogs - pass parent window
WindowGeometryTracker(dialog, settings, section, parent=main_window)

# For main window - no parent
WindowGeometryTracker(main_window, settings, section)
```

## Dialog Caching

After ready, dialogs cache position and size on move/resize (same as main window), but:
- **Never cache maximized state** - dialogs don't maximize
- **Never cache iconized state** - dialogs don't iconize
- **Save on close** - `save()` called in `on_close_editor()`

---

# Part 3: Platform Considerations

## Linux/GTK (X11)

- EVT_MOVE/EVT_SIZE detection needed
- Window manager may move window multiple times before ready
- Correct position/size until active, confirmed, and achieved
- Wait for EVT_IDLE before maximize to ensure correct restore geometry

## Windows/macOS

- Standard positioning works
- No correction needed

## Wayland

- Window positioning disabled by design
- `GetPosition()` always returns (0, 0)
- `SetPosition()` has no effect
- No workaround exists - log warning

---

# Part 4: Technical Background

## Problem Description

### Symptoms
- Window position is saved correctly on close
- On restart, window appears at WM's default position instead of saved position
- Position is typically upper-left of usable screen area

### Environment
- Platform: Linux (X11)
- GUI Toolkit: wxPython 4.x with GTK3 backend
- Window Manager: Various (Openbox, Mutter, KWin, etc.)

## How GTK Window Positioning Works

1. **Window Manager Control**: On X11/GTK, the window manager (WM) controls window placement
2. **Smart Placement**: WMs use algorithms like "smart placement" to position new windows
3. **Position Hints**: Applications can request specific positions via X11 hints:
   - `PPosition` - Program-specified position
   - `USPosition` - User-specified position (WM should honor this)
4. **GDK_HINT_USER_POS**: GTK flag that sets `USPosition` hint, telling WM to honor the position

## What wxWidgets/wxGTK Does (Broken)

wxGTK calls `gtk_window_move()` but does NOT set `GDK_HINT_USER_POS`. Without this hint, the WM ignores application-requested positions.

## Why Our Solution Works

1. We set initial position/size via `SetSize(x, y, w, h)`
2. GTK/WM ignores this and applies "smart placement"
3. We detect wrong position/size via `EVT_MOVE`/`EVT_SIZE`
4. We correct by calling `SetPosition()`/`SetSize()` again
5. After window is mapped and visible, these calls ARE honored
6. We track corrections via confirmed flags
7. On EVT_IDLE, when active and all confirmed, we mark ready
8. Then we do ONE maximize attempt if needed (with correct restore geometry)

## Why Confirmed Flags and EVT_IDLE

The maximize problem: When `Maximize()` is called immediately after `SetPosition()`/`SetSize()`, GTK hasn't finished internally storing the "restore geometry". The maximize captures a stale restore size.

Solution:
- Track that our SetPosition/SetSize corrections have been confirmed by receiving EVT_MOVE/EVT_SIZE
- Only mark ready during EVT_IDLE, ensuring the event loop has processed all pending geometry changes
- Then maximize - GTK now has the correct restore geometry stored

---

# Part 5: Implementation Checklist

## For Task Coach (Implemented)

### Main Window
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

### Dialogs
1. ✅ Constrained to parent's monitor
2. ✅ Missing size → clear all cache, let system decide
3. ✅ Missing position (size valid) → center on parent with saved size
4. ✅ Size too big → clear all cache, let system decide
5. ✅ Position off-screen → keep size, center, clear position cache
6. ✅ Valid → use saved values
7. ✅ Save on close: `on_close_editor()` calls `save()`
8. ✅ Never use maximized/iconized state

## For wxWidgets Project

File a feature request to add `GDK_HINT_USER_POS` support:
- When `SetPosition()` is called, set the hint
- Or add a new method `SetUserPosition()` that explicitly sets the hint

---

# Part 6: Planned Refactoring

**Status:** research started 2026-09-25, paused. Goal: reopen the main
window, the editors and floating panes at their last size and position
without visible jumps, and adapt to monitor changes the way current
desktop apps do.

## Findings

Measured on Linux with openbox (the LXDE window manager) under Xvfb, in
a scratch copy of the app with the tracker's debug logging on:

| Case | What the user sees today |
|------|--------------------------|
| Normal start | Two states: mapped at the 600x400 minimum, then the saved size about 30 ms later. The tracker sends 5 corrections before ready (0.5 s). |
| Saved maximized | Four states in 180 ms: minimum size where the WM puts it, moved, resized, maximized. |
| Editor reopened | Saved position and size in one step. |
| Editor, first open of a tab set | 400x300 (the tracker minimum) instead of the fitted size, tabs scrolled and fields cut off. |
| Saved monitor gone | Saved size and maximized state dropped: 600x400 where the WM puts it. |
| Saved size larger than the monitor | Same: dropped to the minimum. |

Causes:

- The tracker's `SetMinSize((600, 400))` before the first `Show()`
  makes wxGTK map the window at that size and resize it afterwards.
  Without it, the window maps at the saved size directly.
- Openbox ignores the position of a normal window at map time: GTK
  sends it as "program specified", never `USPosition` (Part 4). Adding
  `USER_POS` from Python with `gtk_window_parse_geometry()` just before
  `Show()` does not reach the X server: wxGTK rewrites the size hints
  (checked with `xprop WM_NORMAL_HINTS`). Only a wxGTK change can set
  it.
- `Maximize()` before the first `Show()` shows the window maximized at
  once, but un-maximizing then gives GTK's natural size (269x27, or the
  minimum size when set), not the saved size. On X11 the normal
  geometry has to exist before maximizing (Part 1, rule 6).
- `load()` turns a missing dialog size (-1) into the minimum before the
  dialog rules run, so rule 2 (let the system decide) never applies and
  the fitted size is lost.
- Invalid saved geometry is dropped instead of adapted.

Also:

- Settings never used: `iconized` (window) is never read,
  `parent_offset` (editor sections) is written but never read,
  `monitor_index` is read by `wxhelper.centerOnAppMonitor()` but never
  written.
- The debug position logger runs a 50 ms `wx.CallLater` chain for
  every tracked window until ready, even with `_DEBUG_WINDOW_TRACKING`
  off.
- Corrections run until the window is active, so a move or resize
  before activation is reverted.
- The per-second scheduler blocks the UI thread 60 ms (200 tasks) to
  600 ms (5000 tasks) every second, so interactive resizing stutters
  with large files whatever the geometry code does (see
  [SCHEDULERS.md: Planned Refactoring](SCHEDULERS.md#planned-refactoring)).

Already tried and documented, do not repeat:

- Saving on every `EVT_MOVE`/`EVT_SIZE`: records spurious values from
  `LoadPerspective()`, `SendSizeEvent()` and GTK realization
  ([PYTHON3_MIGRATION_2.md](PYTHON3_MIGRATION_2.md#window-position-tracking-with-aui)).
- Delays with magic numbers (`wx.CallLater(500, ...)`): rejected, same
  section.
- `SetMinSize()`/`SetSizerAndFit()` locking editor sizes
  ([PYTHON3_MIGRATION_1.md](PYTHON3_MIGRATION_1.md)).
- Resize and sash drag cost: toolbar size loop, AUI live resize
  throttling, deferred column resize
  ([PYTHON3_MIGRATION_3.md](PYTHON3_MIGRATION_3.md#aui-divider-drag-visual-feedback)).

## Proposed Design

One placement model and one pure restore function for all windows:

- **Stored per window:** normal rect (x, y, w, h) and maximized. The
  normal rect is updated only while the window is shown, not maximized
  or iconized, and after its restore step has finished. That ignores
  the spurious construction and realization events without the ready,
  confirmed and idle state machine.
- **`restore_rect(saved, work_areas, fallback)`**, no wx, unit tested:
  1. Monitor: the one overlapping the saved rect most. None: the
     parent's monitor (dialogs) or the primary one (main window), with
     the saved size centered on it.
  2. Clamp the size to that work area instead of dropping it; keep the
     minimum.
  3. Shift the position so the window lies inside the work area.
  4. Keep maximized.
- **Apply:**
  - Before the first `Show()`: `SetSize(rect)`. Set the minimum size
    after the first show.
  - X11 main window: after the first map, one `SetPosition()` if the WM
    put it elsewhere, then `Maximize()` if saved maximized. No loop;
    later WM decisions win.
  - Windows and macOS: position and maximized before `Show()` (to
    verify).
  - Wayland: size and maximized only.
- **Dialogs:** the same function, with the parent's monitor as
  fallback; with no saved size the fitted size stays.
- **Floating panes:** after `LoadPerspective()`, clamp each floating
  pane's position and size with the same function.
- **DPI:** check which DPI awareness the Windows builds run with
  (`application.py` only logs it). If per-monitor, store sizes in DIPs
  (`ToDIP()`/`FromDIP()`) so a window moved between monitors with
  different scaling keeps its size. GTK already uses logical pixels.
- Remove the unused settings keys and the debug `wx.CallLater` chain.

## Not Yet Examined

- Jitter while dragging a window border was not measured; the
  findings above are about reopening. Candidates: the scheduler
  blocking above, and `MainWindow.onResize()`, which sets the toolbar's
  size and minimum sizes on every `EVT_SIZE`.
- Xvfb has no compositor and faster timing than a real desktop;
  repeat the table on LXDE before relying on the exact counts.
- Seen once under Xvfb only: opening an editor left a small window
  showing a "Description" tab at the top left of the screen. Check on
  a real desktop.

## How It Was Measured

Set `_DEBUG_WINDOW_TRACKING = True` in a copy of the app, run it with
`--ini` and its own `XDG_CONFIG_HOME` under `Xvfb` plus `openbox`,
reset the `[window]` section before each run (the app saves its
geometry on exit), and poll `xwininfo -id <window>` every 10 ms for the
visible states. `xprop WM_NORMAL_HINTS` shows which position hint
reached the X server.

## Next Steps

1. Ask upstream for `USPosition` on positions set before show (or
   check newer wxWidgets): it would remove the one visible move on X11.
2. Implement `restore_rect()` with unit tests; move the main window,
   editors and floating panes to it.
3. Test on the real desktop (LXDE/openbox) and on Windows: normal,
   maximized, un-maximize, monitor unplugged, smaller monitor, editor
   first and second open, floating pane on a removed monitor.

---

## References

- [wxWidgets/Phoenix Issue #2214](https://github.com/wxWidgets/Phoenix/issues/2214) - Frame position problem on Linux
- [wxWidgets/Phoenix Issue #1217](https://github.com/wxWidgets/Phoenix/issues/1217) - GetHandle() returns XID
- [GTK gtk_window_move() docs](https://docs.gtk.org/gtk3/method.Window.move.html) - WM ignores initial positions
- [Gdk.WindowHints](https://docs.gtk.org/gdk3/flags.WindowHints.html) - USER_POS hint

---

*Document created: 2025-11-23*
*Last updated: 2026-09-25*
