# AUI Docking Issues on Wayland

This document describes known issues with wxPython/wxWidgets AUI (Advanced User Interface) docking functionality when running on Wayland display servers.

## Problem Summary

AUI docking is unusable on Wayland because users cannot see where panes will dock when dragging. The docking hints (visual preview) don't display due to Wayland's security model.

### What Works on Wayland

| Feature | Status | Notes |
|---------|--------|-------|
| Floating windows | ✅ Works | Can detach panes to floating windows |
| Resize panes via sash/dividers | ✅ Works | Dividers work normally |
| Drag floating window around | ✅ Works | Compositor handles movement |

### What's Broken on Wayland

| Feature | Status | Notes |
|---------|--------|-------|
| Docking hints/preview | ❌ Broken | Can't see where pane will dock |
| Drag pane to rearrange docked layout | ❌ Unusable | Works but no visual feedback |
| Drag floating window to re-dock | ❌ Broken | App can't detect dock zones |

## Technical Root Cause

On Wayland, `gdk_window_get_origin()` always returns `(0, 0)` and `gtk_window_move()` does nothing because Wayland intentionally hides global screen coordinates from applications for security. AUI's docking hints use separate overlay windows that require global coordinates to position, so they appear broken or squashed at origin. Same-window operations like sash resizing work because mouse coordinates are relative to that window.

## Target Behavior: GIMP-like Docking

GIMP provides a working docking model on Wayland that we should emulate:

- **Floating windows work** - panes can be detached and moved around
- **Once undocked, panes cannot be re-docked via drag** - this is a Wayland limitation
- **Explicit menu controls** are needed to toggle windows between docked and floating states

This pattern accepts Wayland's limitations while preserving useful functionality.

## Upstream Bug Reports

| Issue | Status | Description |
|-------|--------|-------------|
| [wxWidgets #25722](https://github.com/wxWidgets/wxWidgets/issues/25722) | Open | Main tracking issue for Wayland AUI/miniframe problems |
| [wxWidgets #22576](https://github.com/wxWidgets/wxWidgets/issues/22576) | Fixed | Docking indicator wrong position - fixed with wxOverlay |
| [wxWidgets #18372](https://github.com/wxWidgets/wxWidgets/issues/18372) | Closed (dup) | Floating panes cannot be dragged |
| [wxWidgets #18669](https://github.com/wxWidgets/wxWidgets/issues/18669) | Open | KDE/KWin specific issues |

## Upstream Fix: wxOverlay (Not Yet Available)

wxWidgets C++ fixed docking hints for Wayland in [commit 29c8bfc](https://github.com/wxWidgets/wxWidgets/commit/29c8bfc) (February 9, 2024):

> "Use wxOverlay to show docking hint instead of transparent wxFrame. The main advantage of using wxOverlay over wxFrame, besides reduced code complexity, is that the docking hint now works correctly under Wayland which it didn't work before. wxAUI_MGR_RECTANGLE_HINT now works everywhere (including wxGTK and wxOSX)."

Related commits:
- [29c8bfc](https://github.com/wxWidgets/wxWidgets/commit/29c8bfc) - wxOverlay fix for docking hints (Feb 2024)
- [b1442f2](https://github.com/wxWidgets/wxWidgets/commit/b1442f2) - Restore screen coords in ShowHint() for backward compat (Oct 2024)

**Current status**:
- Fix is in wxWidgets C++ (wx.aui) but requires wxWidgets 3.2.5+
- Fix is NOT in wxPython's pure Python `wx.lib.agw.aui` (which Task Coach uses)
- Current wxPython 4.2.0 ships with wxWidgets 3.2.2 (predates the fix)

**Monitoring**: When wxPython AGW AUI is updated with the wxOverlay approach, or when we can switch to wx.aui with a newer wxWidgets, docking hints should work.

## Task Coach Implementation

**Implemented**:
- `operating_system.isWayland()` detection in `taskcoachlib/operating_system.py`
- "Reset window layout" menu option in View menu:
  - Closes ALL viewers
  - Resets viewer counts to fresh install defaults (1 TaskViewer, 1 CategoryViewer)
  - Clears saved perspective
  - Recreates viewers with default layout (TaskViewer in center, CategoryViewer on right)

### Reset Implementation Details

The reset must handle tabbed/notebook configurations where multiple viewers are stacked. Simply closing viewers leaves orphaned AUI notebook controls that break the center pane detection.

**Solution:**
1. Close all viewers via `closeViewer()`
2. Call `manager.Update()` to process closures
3. Use `DetachPane()` then `ClosePane()` on any remaining non-toolbar panes (cleans up notebook controls)
4. Call `manager.Update()` again
5. Reset viewer counts and perspective in settings
6. Recreate viewers with `addViewers()`
7. **Explicitly set first TaskViewer to `AUI_DOCK_CENTER`** - don't rely on auto-positioning since leftover AUI state can cause `dockedPanes()` to return non-empty, skipping center placement

The explicit CENTER positioning is critical: without a center pane, AUI docking hints disappear entirely and users cannot re-dock floating panes.

**Planned** (GIMP-like pattern):
- Menu options to explicitly create windows as docked or floating
- Menu option to toggle a window between docked and floating state
- This provides explicit control since drag-based docking is unusable on Wayland

## GDK_BACKEND=x11 Is Not a Viable Solution

While `GDK_BACKEND=x11` forces the application onto XWayland where positioning works, this is **NOT** a viable or sustainable solution:

- **User intervention required** — users must set an environment variable or use a wrapper script, with no in-app guidance when popups appear misplaced
- **Loses Wayland-native benefits** — fractional scaling, touchpad gestures, improved security model, better multi-monitor handling
- **XWayland is a compatibility shim** — relying on it means the app never actually works on Wayland
- **Not future-proof** — distributions are moving toward Wayland-only; XWayland may not always be available or fully functional

Each Wayland positioning issue must be solved with a proper Wayland-compatible approach (modal dialogs, xdg_popup windows, compositor-managed positioning).

## Workaround: Run Under XWayland (AUI Docking Only)

> **Note:** This workaround only addresses AUI docking hints. It is not a general solution for Wayland positioning issues — see section above.

XWayland is a compatibility layer that runs an X11 server inside Wayland, allowing legacy X11 applications to run on Wayland systems. Most Wayland compositors (GNOME, KDE Plasma, etc.) include XWayland by default. When an application runs under XWayland, it has access to the X11 APIs that AUI docking requires, including global screen coordinates and window positioning.

To get full AUI docking functionality on a Wayland system, run Task Coach under XWayland by setting the GDK_BACKEND environment variable:

```bash
GDK_BACKEND=x11 taskcoach
GDK_BACKEND=x11 python taskcoach.py
GDK_BACKEND=x11 python3 taskcoach.py
```

This forces the application to use the X11 backend via XWayland, where AUI docking works correctly.

## References

- [xdg-toplevel-drag protocol](https://wayland.app/protocols/xdg-toplevel-drag-v1) - future solution for floating window docking
- [GIMP Docking Documentation](https://docs.gimp.org/2.6/en/gimp-concepts-docks.html) - reference for docking behavior
- [wxWidgets Wayland Support](https://docs.wxwidgets.org/latest/plat_gtk_overview.html)
- [wxAuiManager Class Reference](https://docs.wxwidgets.org/latest/classwx_aui_manager.html)
