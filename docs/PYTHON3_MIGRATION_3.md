# Python 3 Migration Technical Notes - Part 3: GTK and AUI Issues

This document is part of the Python 3 migration documentation. See [PYTHON3_MIGRATION_INDEX.md](PYTHON3_MIGRATION_INDEX.md) for the complete index.

**Contents:**
- [GTK3 Menu Size Allocation Bug](#gtk3-menu-size-allocation-bug)
- [Search Box Visibility in AUI Toolbars](#search-box-visibility-in-aui-toolbars)
- [AUI Divider Drag Visual Feedback](#aui-divider-drag-visual-feedback)
- [GTK BitmapComboBox Icon Clipping](#gtk-bitmapcombobox-icon-clipping)
- [Known Issues](#known-issues)

---

## GTK3 Menu Size Allocation Bug

**Date Fixed:** December 2025
**Affected Components:** File menu, Dynamic menus
**Root Cause:** GTK3 bug where menu size allocation is not calculated on first popup

### Problem Overview

When opening the File menu for the first time, scroll arrows appeared even though there was plenty of screen space to display all menu items. The menu displayed correctly on subsequent opens.

### Symptoms

1. File menu shows scroll arrows on first open
2. Same menu works perfectly on second and subsequent opens
3. All measurable wx/GDK properties are identical between first and second open
4. Problem occurs on multi-monitor setups

### Root Cause Analysis

This is a **known GTK3 bug** where the size allocation for popup menus isn't properly calculated on the first display:

- [GNOME GTK Issue #473](https://gitlab.gnome.org/GNOME/gtk/-/issues/473): GtkMenu has unnecessary scroll handles when menu items are added during popup
- [Stack Overflow discussion](https://stackoverflow.com/questions/14423971/what-is-the-correct-method-to-display-a-large-popup-menu): "So it looks like some-sort of size-allocation issue - its not been calculated on first-popup but is on subsequent pop-up's"
- [Debian Bug #838793](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=838793): Menus are too small in GNOME

The problem was triggered by **modifying menu items during EVT_MENU_OPEN**:

1. GTK creates menu widget lazily on first popup
2. GTK starts calculating size allocation for N items
3. EVT_MENU_OPEN fires, application adds/removes items
4. GTK's size calculation is already done for wrong item count
5. Scroll arrows appear because GTK thinks menu is larger than available space

### The Broken Pattern

The original code modified menu items on every menu open:

```python
class FileMenu(Menu):
    def __init__(self, ...):
        # Build static menu items
        ...
        self._window.Bind(wx.EVT_MENU_OPEN, self.onOpenMenu)

    def onOpenMenu(self, event):
        if event.GetMenu() == self:
            # WRONG: Modifying menu during popup triggers GTK bug
            self.__removeRecentFileMenuItems()
            self.__insertRecentFileMenuItems()
        event.Skip()
```

This pattern was also used in several `DynamicMenuThatGetsUICommandsFromViewer` subclasses that rebuild their entire contents on every `EVT_MENU_OPEN`.

### The Correct Pattern: Pub/Sub Updates

The proper approach is to:
1. Populate menus at initialization time
2. Subscribe to data change notifications via pub/sub
3. Update menu items only when data actually changes
4. Never modify menus during popup

```python
class FileMenu(Menu):
    def __init__(self, ...):
        # Build static menu items
        ...
        # Populate recent files at init (fixes GTK3 menu size bug)
        self.__insertRecentFileMenuItems()

        # Subscribe to settings changes to update recent files list
        # This replaces the broken EVT_MENU_OPEN approach
        pub.subscribe(self.__onRecentFilesChanged, "settings.file.recentfiles")

    def __onRecentFilesChanged(self, value):
        """Update recent files menu when settings change."""
        self.__removeRecentFileMenuItems()
        self.__insertRecentFileMenuItems()
```

### Why TaskTemplateMenu Works Correctly

`TaskTemplateMenu` was already using the correct pattern:

```python
class TaskTemplateMenu(DynamicMenu):
    def registerForMenuUpdate(self):
        pub.subscribe(self.onTemplatesSaved, "templates.saved")
```

It only rebuilds when templates actually change, not on every menu open.

### Files Modified

| File | Change |
|------|--------|
| `taskcoachlib/gui/menu.py` | FileMenu refactored to use pub/sub instead of EVT_MENU_OPEN |

### Key Learnings

1. **Never modify menus during popup**: GTK3 has a bug where size allocation isn't recalculated when items are added/removed during popup. This causes scroll arrows to appear incorrectly.

2. **Use pub/sub for dynamic content**: Instead of rebuilding menus on every open, subscribe to data change events and update only when data changes.

3. **Pre-populate at init**: Build menus with their full content at initialization time so GTK sees the correct size from the start.

4. **The `EVT_MENU_OPEN` trap**: It's tempting to use EVT_MENU_OPEN for updating dynamic content, but this triggers the GTK bug. Use data change notifications instead.

5. **Submenus may be less affected**: The DynamicMenuThatGetsUICommandsFromViewer submenus (ModeMenu, FilterMenu, etc.) use EVT_MENU_OPEN but are smaller and may not trigger visible scroll arrows.

### Testing Checklist

- [ ] Open File menu on first run - should not show scroll arrows
- [ ] Open recent files - menu should update automatically (via pub/sub)
- [ ] Test on multi-monitor setup with different resolutions
- [ ] Test with window near bottom of screen (minimal space for menu)

---

## Search Box Visibility in AUI Toolbars

**Date Fixed:** December 2025
**Affected Components:** SearchCtrl in viewer toolbars (Task List, Categories, etc.)
**Root Cause:** Missing minimum size specification for SearchCtrl in AUI toolbars with NO_AUTORESIZE flag

### Problem Overview

The search boxes in viewer toolbars became invisible or too small to click. The search options icon (magnifying glass with dropdown) was visible, but the text input area for typing search terms was collapsed to zero/minimal width.

### Symptoms

1. Search box text input area not visible in toolbar
2. Only the search icon/button visible
3. Unable to type search terms
4. Issue appeared after wxPython version changes

### Root Cause Analysis

The issue was caused by **missing minimum size specification** combined with **AUI toolbar flags**:

1. **No explicit size on SearchCtrl**: The `SearchCtrl` was added to the toolbar without any size or minimum size specification:
   ```python
   self.searchControl = widgets.SearchCtrl(toolbar, ...)
   toolbar.AddControl(self.searchControl)  # No size specified!
   ```

2. **AUI_TB_NO_AUTORESIZE flag**: The toolbar uses `aui.AUI_TB_NO_AUTORESIZE` (line 27 in toolbar.py), which prevents automatic sizing of controls.

3. **wxPython version behavior change**: The default "best size" calculation for `wx.SearchCtrl` may have changed in newer wxPython versions, causing the text input portion to collapse when no minimum size is specified.

### Historical Note

Investigating the git history revealed that **there was never an explicit size set** for the SearchCtrl:

- The original code (pre-Python 3 migration) had no `SetMinSize()` call
- The `size` parameter in `SearchCtrl.__init__` was used for **bitmap size** (`self.__bitmapSize`), not control width
- The control relied on wxPython's default sizing behavior, which worked in older versions but broke in newer ones

This is a case where **implicit behavior changed** between wxPython versions, causing previously working code to fail.

### The Fix

Added explicit minimum size after creating the SearchCtrl:

```python
# In uicommand.py, Search.appendToToolBar()
self.searchControl = widgets.SearchCtrl(
    toolbar,
    value=searchString,
    style=wx.TE_PROCESS_ENTER,
    matchCase=matchCase,
    includeSubItems=includeSubItems,
    searchDescription=searchDescription,
    regularExpression=regularExpression,
    callback=self.onFind,
)
# Set minimum size to ensure the text input is visible in AUI toolbars
# that use AUI_TB_NO_AUTORESIZE flag
self.searchControl.SetMinSize((150, -1))
toolbar.AddControl(self.searchControl)
```

**Why 150px:**
- Slider controls in the same toolbar use 120px
- Search boxes need more space for typing text
- 150px provides reasonable minimum for search input while not being excessive

### Files Modified

| File | Change |
|------|--------|
| `taskcoachlib/gui/uicommand/uicommand.py` | Added `SetMinSize((150, -1))` to SearchCtrl |

### Key Learnings

1. **Explicit sizes for AUI toolbar controls**: When using AUI toolbars with `AUI_TB_NO_AUTORESIZE`, always specify explicit sizes for controls that need a minimum width.

2. **wxPython version differences**: Default sizing behavior can change between wxPython versions. Code that relies on implicit behavior may break silently.

3. **The `size` parameter trap**: The SearchCtrl's `size` parameter was used for bitmap size, not control size. Always check what parameters actually control.

4. **Compare with working controls**: The slider control (`size=(120, -1)`) provided a reference for how to properly size toolbar controls.

### Testing Checklist

- [ ] Search box visible in Task List toolbar
- [ ] Search box visible in Categories toolbar
- [ ] Search box visible in other viewer toolbars
- [ ] Can click in search box and type search terms
- [ ] Search functionality works (filters items as expected)
- [ ] Search options dropdown menu works (click magnifying glass icon)

---

## AUI Divider Drag Visual Feedback

**Date Fixed:** December 2025
**Affected Components:** AUI panel dividers/sashes, main toolbar positioning
**Root Cause:** Multiple issues - missing MinSize on AUI pane info, toolbar EVT_SIZE feedback loop

### Problem Overview

When dragging panel dividers (sashes) between AUI panes, there was no visual feedback during the drag operation, flickering occurred, and the toolbar positioning was incorrect. Investigation revealed multiple interacting issues.

### Symptoms

1. Dragging divider shows flickering and dropped mouse events
2. Toolbar flickers during any AUI resize operation
3. Panel title bars overlap into toolbar area (cut off at close button X)
4. Resizing outer window fixes positioning, but inner operations break it
5. DoUpdate() taking 50-190ms causing performance issues

### Root Cause Analysis

This issue had **three root causes** that were discovered progressively:

#### Root Cause 1: Missing MinSize on AUI Pane Info

The toolbar pane was created without `MinSize` on the `AuiPaneInfo`:

```python
# BEFORE - No MinSize on pane info
self.manager.AddPane(
    bar,
    aui.AuiPaneInfo()
    .Name("toolbar")
    .ToolbarPane()
    .Top()
    # No MinSize!
)
```

**Why this matters:** AUI uses the **pane info's MinSize** for layout calculations, NOT the window's MinSize. Without it, AUI didn't know to reserve 42px for the toolbar height. This caused panel title bars to be positioned too high, overlapping into the toolbar area.

**Why outer window resize worked:** `mainwindow.onResize()` was setting the toolbar window's MinSize, and `event.Skip()` triggered default handling which recalculated AUI layout correctly. But inner AUI operations (sash drag, maximize, restore) didn't go through onResize, so they used the wrong pane info.

#### Root Cause 2: Toolbar EVT_SIZE Feedback Loop

The `MainToolBar._OnSize()` handler was sending `SendSizeEvent` to the parent on every size change:

```python
# BEFORE - feedback loop
def _OnSize(self, event):
    event.Skip()
    # This was scheduling SendSizeEvent on every toolbar size change
    wx.CallAfter(self.__safeParentSendSizeEvent)
```

This created extra work during sash dragging:
1. AUI resizes panes during drag
2. Toolbar gets EVT_SIZE
3. SendSizeEvent triggers mainwindow.onResize
4. onResize does extra layout work
5. This causes flicker and dropped mouse events

#### Root Cause 3: Wrong MinSize in Realize()

The `MainToolBar.Realize()` method was setting MinSize with `height=-1`:

```python
# BEFORE - wrong height
def Realize(self):
    ...
    wx.CallAfter(self.__safeParentSendSizeEvent)  # Sets height=42 via onResize
    wx.CallAfter(self.__safeSetMinSize, (w, -1))  # Then overwrites with height=-1!
```

### The Complete Fix

**Fix 1: Set MinSize on AUI pane info** (mainwindow.py)

```python
# showToolBar() - set MinSize when creating pane
self.manager.AddPane(
    bar,
    aui.AuiPaneInfo()
    .Name("toolbar")
    .ToolbarPane()
    .Top()
    .MinSize((-1, 42))  # Tell AUI to reserve 42px height
    ...
)

# onResize() - update pane info MinSize, not just window
def onResize(self, event):
    currentToolbar = self.manager.GetPane("toolbar")
    if currentToolbar.IsOk():
        width = event.GetSize().GetWidth()
        currentToolbar.window.SetSize((width, -1))
        currentToolbar.window.SetMinSize((width, 42))
        currentToolbar.MinSize((width, 42))  # NEW: Also set pane info MinSize
    event.Skip()
```

**Fix 2: Remove EVT_SIZE handler** (toolbar.py)

```python
# AFTER - no EVT_SIZE handler
class MainToolBar(ToolBar):
    """Main window toolbar with proper AUI integration.

    The toolbar's space is reserved by setting MinSize on the AUI pane info
    (in mainwindow.showToolBar and onResize). This ensures AUI always
    allocates proper space for the toolbar during layout calculations.

    Note: We intentionally do NOT use EVT_SIZE here. Previously there was
    a handler that sent SendSizeEvent to fix AUI layout miscalculations,
    but this caused performance issues during sash dragging (each drag
    triggered extra layout recalculations). Now that MinSize is properly
    set on the pane info, AUI calculates layout correctly without needing
    the fixup.
    """
    # No __init__ with EVT_SIZE binding
    # No _OnSize handler
```

**Fix 3: Remove wrong SetMinSize in Realize()** (toolbar.py)

```python
# AFTER - only SendSizeEvent, no SetMinSize override
def Realize(self):
    self._agwStyle &= ~aui.AUI_TB_NO_AUTORESIZE
    super().Realize()
    self._agwStyle |= aui.AUI_TB_NO_AUTORESIZE
    # Only SendSizeEvent - onResize will set correct MinSize
    wx.CallAfter(self.__safeParentSendSizeEvent)
    # REMOVED: wx.CallAfter(self.__safeSetMinSize, (w, -1))
```

**Fix 4: Enable AUI_MGR_LIVE_RESIZE** (frame.py)

```python
agwStyle = (
    aui.AUI_MGR_DEFAULT
    | aui.AUI_MGR_ALLOW_ACTIVE_PANE
    | aui.AUI_MGR_LIVE_RESIZE  # Live visual feedback when dragging sashes
)
```

**Fix 5: Throttle sash resize updates** (frame.py)

AUI's `LIVE_RESIZE` mode calls `Update()` on every mouse move, which triggers expensive repaints (50-190ms). Added throttling to limit updates to ~30fps:

```python
def _install_sash_resize_optimization(manager):
    state = {'last_update_time': 0, 'min_update_interval': 0.033}  # ~30fps

    original_on_motion = getattr(manager, 'OnMotion', None)
    if original_on_motion:
        def throttled_on_motion(event):
            action = getattr(manager, '_action', 0)
            if action == 3:  # actionResize (sash drag)
                now = time.time()
                if now - state['last_update_time'] < state['min_update_interval']:
                    event.Skip()
                    return
                state['last_update_time'] = now
            return original_on_motion(event)
        manager.OnMotion = throttled_on_motion
```

**Fix 6: Defer column resize on all platforms** (autowidth.py)

The `AutoColumnWidthMixin` was calling `DoResize()` directly on Linux during EVT_SIZE, causing cascade repaints. Windows already used `wx.CallAfter` to defer this. Changed to defer on all platforms:

```python
def OnResize(self, event):
    event.Skip()
    # Always defer to avoid cascade repaints during AUI sash drag
    wx.CallAfter(self.DoResize)
```

### Investigation Process

This was a complex debugging journey that illustrates the importance of understanding root causes:

1. **Initial symptom**: No visual feedback when dragging dividers
2. **First attempt**: Added `AUI_MGR_LIVE_RESIZE` flag → Made flickering WORSE
3. **Investigation**: Found `DoUpdate()` taking 50-190ms per call
4. **Second attempt**: Added Freeze/Thaw around resize → Still flickered
5. **Key insight**: "Why does resizing outer window work but inner operations don't?"
6. **Root cause found**: MinSize was set on window but not on AUI pane info
7. **Third attempt**: Added MinSize to pane info → Fixed positioning but still slow
8. **Final fix**: Removed unnecessary EVT_SIZE handler → Fixed performance

### Key Learnings

1. **AUI pane info vs window properties**: AUI uses its own `AuiPaneInfo` properties for layout calculations, not the window's properties. Setting `window.SetMinSize()` doesn't tell AUI anything - you must also set `paneInfo.MinSize()`.

2. **Feedback loops are subtle**: The toolbar's EVT_SIZE handler was meant to fix layout issues, but after fixing the root cause (pane info MinSize), it became unnecessary overhead that caused performance issues.

3. **Test both inner and outer resize**: A bug that only appears during inner AUI operations but not outer window resize indicates different code paths - investigate what the working path does differently.

4. **Remove workarounds after fixing root cause**: The EVT_SIZE handler was a workaround for missing MinSize. Once MinSize was properly set, the workaround became harmful.

5. **Legacy code patterns**: The toolbar's EVT_SIZE handler dated back to Windows XP era (~2010) and was no longer needed with proper AUI configuration.

### Files Modified

| File | Change |
|------|--------|
| `taskcoachlib/widgets/frame.py` | Added `AUI_MGR_LIVE_RESIZE` flag, added ~30fps throttling for sash drag |
| `taskcoachlib/gui/mainwindow.py` | Added `.MinSize((-1, 42))` to toolbar pane, added `paneInfo.MinSize()` in onResize |
| `taskcoachlib/gui/toolbar.py` | Removed EVT_SIZE handler and feedback loop code, removed wrong SetMinSize in Realize() |
| `taskcoachlib/widgets/autowidth.py` | Changed `DoResize()` to use `wx.CallAfter` on all platforms, not just Windows |

### Testing Checklist

- [ ] Drag horizontal divider between panels - should see smooth live resize
- [ ] Drag vertical divider between panels - should see smooth live resize
- [ ] Maximize/restore inner panes - toolbar should stay correctly positioned
- [ ] No toolbar flicker during any operation
- [ ] Panel title bars fully visible (not cut off at close button)
- [ ] Resize outer window - layout should be correct
- [ ] No performance issues (dropped mouse events) during sash drag

### Update: Simplified Toolbar Height with GetBestSize()

**Date:** December 2025

The original fix used hardcoded `height=42` for the toolbar pane. This was later simplified to use `GetBestSize()` which automatically calculates the correct height based on icon size.

**Key insight:** The main toolbar is docked at the top and spans full window width. Sash operations on panes below do not affect toolbar size. This means:
1. `AUI_TB_NO_AUTORESIZE` toggling is unnecessary for the main toolbar
2. The toolbar can use standard AUI auto-sizing via `GetBestSize()`
3. `MainToolBar` doesn't need any special overrides

**Simplified code:**

```python
# mainwindow.py - use GetBestSize() instead of hardcoded height
def showToolBar(self, value):
    if value:
        bar = toolbar.MainToolBar(self, self.settings, size=value)
        best_size = bar.GetBestSize()
        self.manager.AddPane(
            bar,
            aui.AuiPaneInfo()
            .Name("toolbar")
            .ToolbarPane()
            .Top()
            .MinSize((-1, best_size.GetHeight()))  # Automatic height!
            .DestroyOnClose(),
        )

# toolbar.py - MainToolBar is now just an empty subclass
class MainToolBar(ToolBar):
    """Main window toolbar for use in AUI-managed main window."""
    pass
```

**Benefits:**
- Automatic height calculation for any icon size (16x16, 22x22, 32x32)
- No hardcoded magic numbers
- Simpler code - MainToolBar has no overrides
- No Freeze/Thaw needed for customization flicker

---

## GTK BitmapComboBox Icon Clipping

**Date Fixed:** December 2025
**Affected Components:** Icon dropdowns in task editor appearance tab, preferences dialog
**Root Cause:** GTK's native BitmapComboBox implementation clips icons in the closed/selected state
**Platform:** GTK/Linux only

### Problem Overview

On GTK/Linux, `wx.adv.BitmapComboBox` displays icons correctly in the dropdown list when opened, but clips the left edge of icons when the dropdown is closed (showing the selected item).

### Symptoms

1. Icon appears cut off on the left side when dropdown is closed
2. Opening the dropdown shows icons correctly in the list
3. Other dropdowns without icons (like `wx.Choice`) don't have this issue
4. Problem only occurs on GTK - Windows and macOS render correctly

### Root Cause Analysis

This is a **known limitation of GTK's native BitmapComboBox implementation**:

- BitmapComboBox on GTK uses native `GtkCellRendererPixbuf` for rendering
- The cell renderer doesn't properly account for icon space in the closed state
- Related issues: [wxWidgets #24563](https://github.com/wxWidgets/wxWidgets/issues/24563), [wxWidgets #11241](https://trac.wxwidgets.org/ticket/11241)

### Attempted Solutions That Failed

1. **`SetMargins()`** - GTK's native implementation ignores margin settings
2. **Padded bitmaps** - Creating bitmaps with transparent left padding caused pixman rendering errors and black backgrounds
3. **`OwnerDrawnComboBox`** - Replacing BitmapComboBox with custom-drawn version caused segfaults on GTK3

### Working Workaround

Oversize the control by setting a generous minimum width, giving GTK more space to render without clipping:

```python
# GTK's native BitmapComboBox clips icons in the closed state.
# Oversizing the control gives the renderer more space to work with.
if operating_system.isGTK():
    longestLabel = max(
        (artprovider.chooseableItemImages[name] for name in imageNames),
        key=len
    )
    textWidth, _ = self.GetTextExtent(longestLabel)
    # icon (16) + text + extra padding (16) + dropdown button (30)
    minWidth = 16 + textWidth + 16 + 30
    self.SetMinSize(wx.Size(minWidth, -1))
```

### Files Modified

- `taskcoachlib/gui/dialog/entry.py` - `IconEntry` class
- `taskcoachlib/gui/dialog/preferences.py` - `addAppearanceSetting()` method

### Notes

- The workaround is **GTK-specific** using `operating_system.isGTK()` check
- Windows and macOS users are not affected by the extra width
- This is a cosmetic workaround, not a complete fix - some minor clipping may still be visible
- A proper fix would require changes in wxWidgets/wxPython's GTK integration

---

## Known Issues

### Pending Issues

*None currently documented. Add issues here as they are discovered.*

### Resolved Issues

- Widget resizing stuck at large sizes (November 2025)
- wxPython 4.2.0 category background coloring (Documented in CRITICAL_WXPYTHON_PATCH.md)
- wx.Timer crash when closing Edit Task/Categories quickly (November 2025)
- Hacky close delay patches removed after root cause fix (November 2025)
- Ctrl+C crash with AUI event handler assertion (November 2025)
- Twisted framework removed, replaced with native wxPython + stdlib (November 2025)
- Window position not remembered due to AUI + GTK spurious events (November 2025)
- AUI pane flickering during startup fixed with Freeze/Thaw (November 2025)
- GTK/Linux window position persistence - WM ignores initial position (November 2025) - See [WINDOW_POSITION_PERSISTENCE_ANALYSIS.md](WINDOW_POSITION_PERSISTENCE_ANALYSIS.md)
- GTK3 menu scroll arrows on first open (December 2025) - FileMenu refactored to use pub/sub
- Search box text input invisible in AUI toolbars (December 2025) - Added SetMinSize to SearchCtrl
- AUI divider drag has no visual feedback (December 2025) - Added AUI_MGR_LIVE_RESIZE, throttling, and deferred column resize
- GTK BitmapComboBox icon clipping (December 2025) - Oversized control width as workaround
- Main toolbar flicker on customization (December 2025) - Simplified to use GetBestSize() for automatic height
- File locking library deprecated (December 2025) - Replaced lockfile with fasteners
- App icon grouping across platforms (December 2025) - Added WM_CLASS, StartupWMClass, CFBundleIdentifier, AppUserModelID
- GNOME Wayland app icon shows generic gear (December 2025) - Added g_set_prgname via ctypes before GTK init
- Python 3.12+ SyntaxWarning for invalid escape sequence (December 2025) - Fixed with raw string in desktop module docstring
- Error popup showing without errors (December 2025) - Replaced RedirectedOutput hack with simple log_message/log_error functions

---

**Previous:** [Part 2: Library Cleanup and Framework Removal](PYTHON3_MIGRATION_2.md)

**Next:** [Part 4: Infrastructure, i18n, and Feature Removals](PYTHON3_MIGRATION_4.md)

**Last Updated:** January 2026
