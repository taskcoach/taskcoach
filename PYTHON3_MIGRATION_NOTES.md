# Python 3 Migration Technical Notes

This document captures technical issues, fixes, and refactorings discovered during the migration of Task Coach from Python 2 to Python 3.

## Table of Contents

1. [Widget Resizing Issues](#widget-resizing-issues)
2. [wx.Timer Crash During Window Destruction](#wxtimer-crash-during-window-destruction)
3. [wxPython Compatibility](#wxpython-compatibility)
4. [Known Issues](#known-issues)
5. [Future Work](#future-work)

---

## Widget Resizing Issues

### Problem Overview

**Date Fixed:** November 2025
**Affected Components:** Editor dialogs, Viewer panels, VirtualListCtrl widgets
**Root Cause:** Multiple layers of MinSize locking preventing widgets from shrinking after growing

### Symptoms

1. **Initial Layout Broken:** Widgets would appear squashed (~200x200px) on first render
2. **Stuck at Large Sizes:** After expanding the effort viewer (which could grow to 3021px width), resizing the window smaller would not shrink the widgets back down
3. **Non-responsive UI:** Users could not resize editor dialogs to reasonable sizes

### Root Cause Analysis

The problem was caused by **4 separate layers** where wxPython's sizing system was locking MinSize values:

#### Layer 1: AuiNotebook Perspective (editor.py:1408)
```python
# BEFORE - Broken
self.LoadPerspective(perspective)

# AFTER - Fixed
# DISABLED: LoadPerspective was restoring stale AuiNotebook perspective with broken sizing
# self.LoadPerspective(perspective)
pass
```

**Why it failed:** `LoadPerspective()` was restoring a stale AuiNotebook perspective that contained broken sizing information from previous sessions.

#### Layer 2: Viewer.initLayout() (base.py:212)
```python
# BEFORE - Broken
self.SetSizerAndFit(self._sizer)

# AFTER - Fixed
self.SetSizer(self._sizer)  # Changed from SetSizerAndFit to prevent locking MinSize
```

**Why it failed:** `SetSizerAndFit()` was locking the Viewer's MinSize to the widget's current BestSize during initial layout.

#### Layer 3: BookPage.fit() (notebook.py:65)
```python
# BEFORE - Broken
self.SetSizerAndFit(self._sizer)

# AFTER - Fixed
self.SetSizer(self._sizer)  # Changed from SetSizerAndFit to prevent locking MinSize
```

**Why it failed:** `SetSizerAndFit()` was locking the BookPage's MinSize to its current size, affecting ALL widgets in the page including toolbar.

#### Layer 4: EditBook.addPages() (editor.py:1268-1270)
```python
# BEFORE - Broken
width, height = self.__get_minimum_page_size()
self.SetMinSize((width, self.GetHeightForPageHeight(height)))

# AFTER - Fixed
# DISABLED: SetMinSize was locking entire notebook to max page size
# width, height = self.__get_minimum_page_size()
# self.SetMinSize((width, self.GetHeightForPageHeight(height)))
```

**Why it failed:** EditBook was calculating `max(all page MinSizes)` and locking the entire notebook. When the Effort page had MinSize=3021px, the entire notebook was locked at 3021px width.

### Additional Fixes for GetEffectiveMinSize()

Even after removing the explicit `SetMinSize()` calls, widgets still wouldn't shrink because wxPython's `GetEffectiveMinSize()` returns `max(MinSize, BestSize)`. Two additional fixes were needed:

#### Fix 5: VirtualListCtrl.__init__() (listctrl.py:53)
```python
# Override GetEffectiveMinSize() which returns BestSize - allows sizer to shrink widget
self.SetMinSize((100, 50))
```

**Why needed:** Without this, `GetEffectiveMinSize()` would return the widget's BestSize (which could be 3021px), preventing the sizer from shrinking it.

#### Fix 6: Viewer.initLayout() (base.py:214)
```python
self.SetSizer(self._sizer)
# Prevent GetEffectiveMinSize() from returning child's BestSize
self.SetMinSize((100, 50))
```

**Why needed:** The Viewer panel itself needed a MinSize override to prevent `GetEffectiveMinSize()` from returning its child's BestSize. This allows the BookPage's GridBagSizer to properly resize the Viewer.

### Summary of All Fixes

| Fix | File | Line | Change | Reason |
|-----|------|------|--------|--------|
| 1 | editor.py | 1408 | Disabled `LoadPerspective()` | Stale perspective with broken sizing |
| 2 | base.py | 212 | `SetSizerAndFit()` → `SetSizer()` | Prevent locking Viewer MinSize |
| 3 | notebook.py | 65 | `SetSizerAndFit()` → `SetSizer()` | Prevent locking BookPage MinSize |
| 4 | editor.py | 1268-1270 | Disabled `SetMinSize()` | Prevent locking notebook to max page size |
| 5 | listctrl.py | 53 | Added `SetMinSize((100, 50))` | Override GetEffectiveMinSize() for widgets |
| 6 | base.py | 214 | Added `SetMinSize((100, 50))` | Override GetEffectiveMinSize() for Viewer panel |

### Key Learnings

1. **SetSizerAndFit() is dangerous:** In dynamic layouts, `SetSizerAndFit()` can lock MinSize values based on initial content, preventing future resizing.

2. **GetEffectiveMinSize() behavior:** wxPython returns `max(MinSize, BestSize)`, so even with no explicit MinSize, widgets can't shrink below their BestSize without setting a small MinSize override.

3. **Cascading size constraints:** Size constraints can cascade through multiple widget layers (Notebook → BookPage → Viewer → VirtualListCtrl). All layers must be fixed for resizing to work properly.

4. **AuiNotebook perspective persistence:** Perspective strings can become stale and carry broken sizing information across sessions.

### Testing Checklist

When working on sizing issues in the future, test:

- [ ] Initial dialog render (should not be squashed)
- [ ] Expand effort viewer with many columns
- [ ] Shrink window back to small size
- [ ] Switch between different editor tabs
- [ ] Close and reopen editor (persistence test)
- [ ] Multiple resize cycles (grow → shrink → grow → shrink)

---

## wx.Timer Crash During Window Destruction

### Problem Overview

**Date Fixed:** November 2025
**Affected Components:** All widgets and dialogs using wx.Timer
**Root Cause:** wx.Timer firing after window/widget destruction causes segfault

### Symptoms

1. **Crash on Quick Close:** Closing dialogs quickly causes a segmentation fault with backtrace showing:
   ```
   #0  0x0000000000000000 in  ()  // NULL pointer crash
   #1  wxEvtHandler::SafelyProcessEvent(wxEvent&)
   #2  wxTimerImpl::SendEvent()
   #3  sipwxTimer::Notify()
   ```
2. **GTK-specific:** The crash primarily occurs on GTK/Linux platforms
3. **No Python Traceback:** The crash occurs in C++ code with address 0x00000000
4. **Timing-dependent:** Only crashes if window closed before timer fires (typically <500ms)

### Root Cause Analysis

The crash was caused by **multiple wx.Timer instances** continuing to run after window destruction:

**Why it crashes:**
1. Widget creates a wx.Timer with callback to itself
2. User closes window/widget **before timer fires**
3. Window is destroyed but timer continues running in GTK event loop
4. Timer fires and tries to call callback on **destroyed object** (NULL pointer)
5. Segfault occurs at address 0x00000000 in wxWidgets C++ code

**Why "waiting a few seconds" prevents the crash:**
- One-shot timers (like SearchCtrl's 500ms debounce) fire and complete
- Once fired, no pending timer exists, so no crash on close
- This is why the crash is **timing-dependent**

This is a **known wxPython issue**:
- [Phoenix Issue #429](https://github.com/wxWidgets/Phoenix/issues/429): Timer causes hard crash during shutdown
- [Phoenix Issue #632](https://github.com/wxWidgets/Phoenix/issues/632): Crash if wx.Timer isn't stopped before window closes

### All Timers Fixed

A comprehensive audit found **9 wx.Timer instances** that needed cleanup:

| Component | File | Timer Type | Delay | Fix Applied |
|-----------|------|------------|-------|-------------|
| **SearchCtrl** | searchctrl.py | One-shot debounce | 500ms | EVT_WINDOW_DESTROY + refactored |
| **wxScheduler** | wxScheduler.py | One-shot refresh | Up to 60s | EVT_WINDOW_DESTROY |
| **wxScheduler** | wxScheduler.py | One-shot resize | 250ms | EVT_WINDOW_DESTROY |
| **TreeListMainWindow** | hypertreelist.py | One-shot drag | 250ms | EVT_WINDOW_DESTROY |
| **SmartDateTimeCtrl** | smartdatetimectrl.py | One-shot reset | 2000ms | Stop in Cleanup() |
| **ToolTipMixin** | tooltip.py | One-shot tooltip | 200ms | EVT_WINDOW_DESTROY |
| **StatusBar** | status.py | Delayed update | 500ms | Stop in Destroy() |
| **SecondRefresher** | refresher.py | Repeating | 1000ms | Stop in removeInstance() |
| **NotificationCenter** | notifier_universal.py | Repeating | 1000ms | Stop in app shutdown |

### The Modern Fix Pattern: EVT_WINDOW_DESTROY

The **best practice** is to use `EVT_WINDOW_DESTROY` for automatic cleanup:

```python
class MyWidget(wx.Window):
    def __init__(self, parent):
        super().__init__(parent)
        self.__timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onTimer, self.__timer)
        # CRITICAL: Bind to EVT_WINDOW_DESTROY for automatic cleanup
        self.Bind(wx.EVT_WINDOW_DESTROY, self._onDestroy)
        self.__timer.Start(500, oneShot=True)

    def _onDestroy(self, event):
        """Automatically cleanup timer on window destruction."""
        if event.GetEventObject() == self:
            if self.__timer and self.__timer.IsRunning():
                self.__timer.Stop()
        event.Skip()  # MUST call Skip() to continue destruction chain
```

**Why this is better than manual cleanup() calls:**
1. **Automatic** - No need to remember to call cleanup()
2. **Reliable** - Guaranteed to run during widget destruction
3. **Crash-safe** - Runs even if window closed unexpectedly
4. **Idempotent** - Can be called multiple times safely

### SearchCtrl: Modern Best Practices Refactoring

The SearchCtrl timer was refactored to follow modern best practices:

#### Before (Magic Numbers, No Auto-Cleanup)
```python
def onFindLater(self, event):
    self.__timer.Start(500, oneShot=True)  # Magic number!

def cleanup(self):  # Never called automatically!
    if self.__timer.IsRunning():
        self.__timer.Stop()
```

#### After (Named Constants, Auto-Cleanup, Configurable)
```python
class SearchCtrl(wx.SearchCtrl):
    # Named constant instead of magic number
    SEARCH_DEBOUNCE_DELAY_MS = 500

    def __init__(self, *args, **kwargs):
        # Configurable delay for different use cases
        self.__debounceDelay = kwargs.pop("debounceDelay", self.SEARCH_DEBOUNCE_DELAY_MS)
        super().__init__(*args, **kwargs)
        self.__timer = wx.Timer(self)
        # Auto-cleanup via EVT_WINDOW_DESTROY
        self.Bind(wx.EVT_WINDOW_DESTROY, self._onDestroy)

    def onFindLater(self, event):
        """
        Debounce search operations using a timer.

        This implements the "search-as-you-type" debouncing pattern:
        - Restarts the timer on each keystroke
        - Only triggers the actual search after user stops typing
        - Prevents expensive filtering operations on every character

        This is a best practice for search UX, used by Google, VS Code, etc.
        """
        self.__timer.Start(self.__debounceDelay, oneShot=True)

    def _onDestroy(self, event):
        """Automatically cleanup timer on window destruction."""
        if event.GetEventObject() == self:
            self.cleanup()
        event.Skip()

    def cleanup(self):
        """Stop the timer and clear callback to prevent crashes."""
        if self.__timer and self.__timer.IsRunning():
            self.__timer.Stop()
        self.__callback = lambda *args, **kwargs: None
```

**Benefits:**
- Named constant (SEARCH_DEBOUNCE_DELAY_MS) instead of magic number
- Configurable delay via constructor parameter
- Comprehensive documentation of debouncing pattern
- Automatic cleanup via EVT_WINDOW_DESTROY
- Idempotent cleanup() method with safety checks

### Why One-Shot Timers Cause "Quick Close" Crashes

One-shot timers (like SearchCtrl's debounce) explain the timing-dependent crashes:

```python
# User types in search box
self.__timer.Start(500, oneShot=True)  # Timer will fire in 500ms

# User closes window IMMEDIATELY (< 500ms later)
# Window destroyed, but timer still pending in GTK event loop

# 500ms after typing, timer fires
# Tries to call callback on DESTROYED widget
# NULL pointer crash at 0x00000000
```

**If user waits >500ms:** Timer fires normally, no crash
**If user closes quickly (<500ms):** Timer fires after destruction, crash

This is why the user observed: *"it doesn't crash if I wait a few seconds before closing the window"*

### Key Learnings

1. **wx.Timer must be explicitly stopped:** Unlike child windows, timers are not automatically stopped when their parent window is destroyed. The timer's "owner" is really just the target for events, not a true parent-child relationship.

2. **EVT_WINDOW_DESTROY is the safest pattern:** Automatic cleanup via event binding is more reliable than manual cleanup() calls which can be forgotten.

3. **One-shot timers are the most dangerous:** They create timing-dependent crashes that only occur when closing quickly. Repeating timers are more obvious because they crash consistently.

4. **Callbacks hold references:** The timer's callback holds a reference to widgets/objects, which can prevent proper cleanup and create dangling pointers.

5. **GTK async cleanup:** GTK performs asynchronous cleanup that can crash if timers fire during widget destruction.

6. **This is a wxWidgets "wontfix":** The wxWidgets team considers this the application's responsibility, not a bug to fix in the framework.

7. **Magic numbers are debugging nightmares:** Using named constants (SEARCH_DEBOUNCE_DELAY_MS) makes it much easier to understand timer delays during debugging.

8. **Debouncing is a best practice:** The timer pattern itself is sound - it's standard UX for search-as-you-type. The issue was missing cleanup, not the pattern itself.

### Complete Debugging Setup for Timer Crashes

**Date Implemented:** November 2025

We have a comprehensive debugging infrastructure that helps diagnose timer crashes and other segfaults. The tools are designed to have **zero runtime cost** unless explicitly enabled.

#### Debug Tools Available:

| Tool | Always On? | Runtime Cost | When to Use |
|------|-----------|--------------|-------------|
| faulthandler | ✅ Yes | ZERO (only outputs on crash) | Python-level crash diagnosis |
| sys.tracebacklimit | ✅ Yes | ZERO (only affects errors) | Full stack traces on exceptions |
| wx verbose logging | ✅ Yes (GTK only) | Console output only | Debugging wx events/widget lifecycle |
| .gdbinit_taskcoach | Manual | ZERO (only when using GDB) | C++ level crash diagnosis |

#### 1. Faulthandler (Always Enabled)

Python's `faulthandler` module is enabled in `taskcoach.py` and provides automatic crash diagnosis:

```python
import faulthandler
faulthandler.enable(all_threads=True)  # Zero runtime cost!
sys.tracebacklimit = 100  # Full stack traces
```

**What this provides:**
- Python traceback on segfaults showing the exact Python code that was executing
- Stack trace for ALL Python threads at the time of the crash (critical for threading issues)
- Output to stderr (visible in console when running from terminal)
- **Zero performance impact during normal operation**

**How to use:**
1. Run Task Coach from terminal: `python taskcoach.py`
2. Reproduce the crash
3. Check terminal output for the faulthandler traceback
4. The traceback will show the Python call stack leading to the segfault

**Example output:**
```
Fatal Python error: Segmentation fault

Current thread 0x00007f8b4c7fe700 (most recent call first):
  File "/usr/lib/python3/dist-packages/wx/core.py", line 2262 in MainLoop
  File "/usr/lib/python3/dist-packages/twisted/internet/wxreactor.py", line 151 in run
  File "/taskcoachlib/application/application.py", line 263 in start
  File "/taskcoach.py", line 89 in start
```

#### 2. wxPython Verbose Logging (Always Enabled on GTK)

wxPython verbose logging is automatically enabled on GTK/Linux to help diagnose crashes:

**What this provides:**
- All wx events logged to console (EVT_PAINT, EVT_SIZE, etc.)
- Widget creation/destruction messages
- Timer events and bindings
- Helpful for identifying which wx events occur before crashes
- **Only visible when running from terminal** - GUI-only users never see this

**Example output when running from terminal:**
```bash
python taskcoach.py

07:35:49 PM: Debug: Adding duplicate image handler for 'Windows bitmap file'
07:35:49 PM: Debug: Adding duplicate animation handler for '1' type
...
```

**Why always-on:**
- Task Coach is still in active development/refactoring
- Only visible to developers running from terminal
- GUI users (clicking the icon) never see console output
- Provides automatic crash context when running under GDB or from terminal
- No performance impact, only console output

#### 3. GDB for C++ Level Backtraces

For crashes deep in wxPython/GTK C++ code (like `wx.core.MainLoop`), you need C++ level backtraces. We have a custom `.gdbinit_taskcoach` that automates crash analysis.

**Setup:**
```bash
# Install debug symbols (Debian/Ubuntu)
sudo apt-get install python3-dbg libwxgtk3.2-1-dbg gdb
```

**Method 1: Use .gdbinit_taskcoach (Recommended)**

The `.gdbinit_taskcoach` file in the repository root automatically prints backtraces when crashes occur:

```bash
# Run with automatic crash analysis
gdb -x .gdbinit_taskcoach --args .venv/bin/python3 taskcoach.py

# In GDB, just type:
(gdb) run

# When crash occurs, you'll automatically see:
# - C++ backtrace showing crash location
# - Python backtrace if available
# - All threads backtraces
# - Helpful analysis commands
```

**What .gdbinit_taskcoach does:**
- Automatically catches segfaults
- Prints complete C++ backtrace showing NULL pointer crashes
- Prints Python backtrace showing which Python code was executing
- Shows all threads (helpful for threading issues)
- Provides helpful commands for further analysis

**Method 2: Manual GDB**

If you need more control:

```bash
gdb --args .venv/bin/python3 taskcoach.py

# In GDB:
(gdb) run

# When it crashes:
(gdb) bt                   # C++ backtrace (shows 0x00000000 NULL crashes)
(gdb) py-bt                # Python backtrace (which Python code was running)
(gdb) thread apply all bt  # All threads C++ backtraces
(gdb) info threads         # Show all active threads
(gdb) frame 0              # Examine crash frame
(gdb) print <variable>     # Inspect variables
```

**Method 3: Analyze Core Dumps**

If you have a core dump file from a previous crash:

```bash
# Enable core dumps (run once)
ulimit -c unlimited

# Run the app normally
python3 taskcoach.py

# After crash, find core file (usually in /var/lib/systemd/coredump/ or current dir)
# Analyze the core:
gdb .venv/bin/python3 /path/to/core

# In GDB:
(gdb) bt                   # See where it crashed
(gdb) thread apply all bt  # All threads
(gdb) py-bt                # Python context
```

**Method 4: Attach to Running Process**
```bash
# Get process ID
ps aux | grep taskcoach

# Attach GDB to running process
sudo gdb -p <PID>

# Wait for crash or trigger it, then:
(gdb) bt
```

#### 4. Interpreting Crash Output

**Example Timer Crash:**

When a timer crashes, you'll see this pattern in GDB:

```
#0  0x0000000000000000 in  ()           ← NULL pointer (destroyed callback)
#1  wxEvtHandler::SafelyProcessEvent()  ← Trying to deliver event
#2  wxTimerImpl::SendEvent()            ← Timer is firing
#3  sipwxTimer::Notify()                ← wxPython wrapper
#4  [GTK event loop]                    ← Deep in event loop
```

**Analysis:**
- `#0  0x0000000000000000` = Trying to call a NULL pointer (destroyed callback function)
- This means a wx.Timer fired **after** its event handler was destroyed
- The widget/window that owned the timer no longer exists
- The timer callback address is now 0x0000000000000000 (NULL)

**Common Timer Crash Patterns:**

| Crash Address | Meaning | Root Cause |
|--------------|---------|------------|
| `0x0000000000000000` | NULL pointer | Timer callback destroyed |
| `0x0000000000000029` | Nearly NULL | Destroyed event handler |
| `typeinfo for wxEvtHandler` | RTTI info | Accessing destroyed C++ object |
| Random hex address | Dangling pointer | Object freed but timer still running |

**Python-level Crash (from faulthandler):**

```
Fatal Python error: Segmentation fault

Current thread 0x00007f8b4c7fe700 (most recent call first):
  File "/usr/lib/python3/dist-packages/wx/core.py", line 2262 in MainLoop
  File "/twisted/internet/wxreactor.py", line 151 in run
  File "/taskcoachlib/application/application.py", line 263 in start
```

**Analysis:**
- The crash is **in** `wx.core.MainLoop` (C++ event loop) - this is the **symptom**
- The crash is **from** a timer/callback firing - this is the **root cause**
- faulthandler shows **what Python code was running** (MainLoop)
- GDB shows **what actually crashed** (NULL pointer at timer callback)

**Debugging Workflow:**

1. **Check faulthandler output** - Shows which Python code was executing
2. **Look for patterns** - Does it crash on dialog close? On app exit? When typing?
3. **Run under GDB** - Shows the actual NULL pointer and which timer crashed
4. **Check wx verbose logs** - Shows wx events before crash (automatically enabled on GTK)
5. **Search for timers** - Look for `wx.Timer` in the relevant widgets
6. **Verify cleanup** - Ensure timer.Stop() is called in EVT_WINDOW_DESTROY

### Testing Checklist

When working with wx.Timer in the future, test all timing scenarios:

**SearchCtrl (500ms debounce timer):**
- [ ] Type in search box and close dialog immediately (< 500ms)
- [ ] Type in search box, wait for search to complete, then close
- [ ] Rapid typing with quick close
- [ ] Clear search with X button and close immediately

**Dialog Operations:**
- [ ] Open dialog and press ESC immediately (< 100ms)
- [ ] Open dialog, interact with UI, close quickly
- [ ] Rapid open/close cycles (10+ times in rapid succession)

**Window Resizing (wxScheduler 250ms resize timer):**
- [ ] Resize window and close immediately (< 250ms)
- [ ] Resize rapidly then close

**Drag Operations (TreeListMainWindow 250ms drag timer):**
- [ ] Start drag and close immediately (< 250ms)
- [ ] Start drag, wait, then close

**Platform Testing:**
- [ ] Test on GTK/Linux (most prone to timer crashes)
- [ ] Test on Windows (less common but still possible)
- [ ] Test on macOS (different event loop behavior)

**Debugging:**
- [ ] Run under GDB to verify no timer crashes
- [ ] Check faulthandler output in console
- [ ] Monitor for NULL pointer crashes at 0x00000000
- [ ] Verify all timers stopped during destruction using wx debug logs

---

## wxPython Compatibility

### wxPython 4.2.0 Issues

See [CRITICAL_WXPYTHON_PATCH.md](CRITICAL_WXPYTHON_PATCH.md) for details on the category row background coloring bug in wxPython 4.2.0 shipped with Debian Bookworm.

### Version Requirements

- **Minimum:** wxPython 4.2.1-unicode
- **Recommended:** wxPython 4.2.1 or higher
- **Debian Bookworm:** Requires patch (see CRITICAL_WXPYTHON_PATCH.md)

---

## Known Issues

### Pending Issues

*None currently documented. Add issues here as they are discovered.*

### Resolved Issues

- ✅ Widget resizing stuck at large sizes (November 2025)
- ✅ wxPython 4.2.0 category background coloring (Documented in CRITICAL_WXPYTHON_PATCH.md)
- ✅ wx.Timer crash when closing Edit Task/Categories quickly (November 2025)
- ✅ Hacky close delay patches removed after root cause fix (November 2025)

---

## Future Work

### Areas for Investigation

1. **AuiNotebook Perspective Management**
   - Consider removing perspective persistence entirely
   - Or implement perspective validation before restoring
   - Current solution: Perspective disabled for editor dialogs

2. **Size Constraint Architecture**
   - Review all uses of `SetSizerAndFit()` in codebase
   - Document where `SetMinSize()` is actually needed vs. harmful
   - Consider creating wrapper methods with safer defaults

3. **Python 3 String Handling**
   - Audit all string/unicode handling
   - Ensure consistent use of str vs bytes
   - Review file I/O encoding

4. **Deprecated wxPython APIs**
   - Review all wx.FONTSTYLE_* usage
   - Check for other deprecated constants/methods

---

## Contributing to This Document

When adding new technical notes:

1. Include the date the issue was discovered/fixed
2. Provide before/after code examples
3. Explain the root cause, not just the symptoms
4. Add testing checklists when applicable
5. Link to related issues/PRs when available

---

**Last Updated:** November 19, 2025
