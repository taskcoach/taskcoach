# Python 3 Migration Technical Notes

This document captures technical issues, fixes, and refactorings discovered during the migration of Task Coach from Python 2 to Python 3.

## Table of Contents

1. [Widget Resizing Issues](#widget-resizing-issues)
2. [wx.Timer Crash During Window Destruction](#wxtimer-crash-during-window-destruction)
3. [Ctrl+C Crash with AUI Event Handler Assertion](#ctrlc-crash-with-aui-event-handler-assertion)
4. [wxPython Compatibility](#wxpython-compatibility)
5. [Bundled Third-Party Library Cleanup](#bundled-third-party-library-cleanup)
6. [Twisted Framework Removal](#twisted-framework-removal)
7. [Window Position Tracking with AUI](#window-position-tracking-with-aui)
8. [GTK3 Menu Size Allocation Bug](#gtk3-menu-size-allocation-bug)
9. [Search Box Visibility in AUI Toolbars](#search-box-visibility-in-aui-toolbars)
10. [AUI Divider Drag Visual Feedback](#aui-divider-drag-visual-feedback)
11. [GTK BitmapComboBox Icon Clipping](#gtk-bitmapcombobox-icon-clipping)
12. [Known Issues](#known-issues)
13. [Future Work](#future-work)

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

## Ctrl+C Crash with AUI Event Handler Assertion

### Problem Overview

**Date Fixed:** November 2025
**Affected Components:** Application shutdown, signal handling
**Root Cause:** AUI manager event handlers not cleaned up before wxPython atexit handler runs

### Symptoms

When pressing Ctrl+C in the console while Task Coach is running:

```
^CException ignored in atexit callback: <built-in function _wxPyCleanup>
wx._core.wxAssertionError: C++ assertion "GetEventHandler() == this" failed at
./src/common/wincmn.cpp(473) in ~wxWindowBase(): any pushed event handlers must have been removed
```

### Root Cause Analysis

The problem was caused by the interaction between **signal handling** and **wxPython AUI**:

1. **AUI (Advanced User Interface) manager** pushes event handlers onto windows for dock/float functionality
2. When Ctrl+C is pressed, Python handles SIGINT
3. Without proper cleanup, wxPython's atexit handler finds windows with pushed event handlers → assertion error
4. `manager.UnInit()` must be called **before** Python's final cleanup runs

### The Fix

Use **Python's atexit module** to register cleanup that runs before wxPython's cleanup:

```python
# In application.py __register_signal_handlers()
import signal
import atexit

def cleanup_wx():
    """Clean up wx before Python exit."""
    try:
        if hasattr(self, 'mainwindow') and hasattr(self.mainwindow, 'manager'):
            self.mainwindow.manager.UnInit()
    except Exception:
        pass  # Best effort cleanup

# Register cleanup via atexit (runs before Python's final cleanup)
atexit.register(cleanup_wx)

def sigint_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    wx.CallAfter(self.quitApplication)

# Register SIGINT handler for Unix Ctrl+C
if not operating_system.isWindows():
    signal.signal(signal.SIGINT, sigint_handler)
```

**Why this works:**
- `atexit.register()` handlers run **before** wxPython's atexit cleanup
- `manager.UnInit()` properly pops all AUI event handlers
- The SIGINT handler uses `wx.CallAfter()` to cleanly quit through the main loop

### Also Keep onClose() Cleanup

For normal window close (clicking X button), keep `manager.UnInit()` in `mainwindow.onClose()`:

```python
def onClose(self, event):
    # ... other cleanup ...
    if application.Application().quitApplication():
        self.manager.UnInit()  # Clean up AUI before window destruction
        event.Skip()
```

### Key Lessons Learned

1. **AUI managers must call UnInit()** before window destruction to avoid assertion errors
2. **atexit handlers** run in LIFO order, so registering cleanup early ensures it runs before wx cleanup
3. **Signal handlers should use wx.CallAfter()** to schedule quit on the main thread

### Testing Checklist

- [ ] Start app, press Ctrl+C - should exit cleanly without assertion error
- [ ] Start app, close via window X button - should exit cleanly
- [ ] Start app, use File > Quit menu - should exit cleanly
- [ ] Start app, send SIGTERM (`kill <pid>`) - should exit cleanly

### References

- [AUI error discussion](https://discuss.wxpython.org/t/aui-error-any-pushed-event-handlers-must-have-been-removed/34555)
- [wxFormBuilder UnInit issue](https://github.com/wxFormBuilder/wxFormBuilder/issues/623)

---

## wxPython Compatibility

### wxPython 4.2.0 Issues

See [CRITICAL_WXPYTHON_PATCH.md](CRITICAL_WXPYTHON_PATCH.md) for details on the category row background coloring bug in wxPython 4.2.0 shipped with Debian Bookworm.

### Version Requirements

- **Minimum:** wxPython 4.2.1-unicode
- **Recommended:** wxPython 4.2.1 or higher
- **Debian Bookworm:** Requires patch (see CRITICAL_WXPYTHON_PATCH.md)

---

## Bundled Third-Party Library Cleanup

During the Python 3 migration, several bundled third-party libraries were evaluated for removal or replacement. Task Coach historically bundled many libraries to ensure compatibility across platforms.

### ntlm/ Module

**Date Evaluated:** November 2025
**Location:** `taskcoachlib/thirdparty/ntlm/`
**Source:** https://github.com/bendyer/python-ntlm (2011)

#### Analysis Results

| File | Status | Notes |
|------|--------|-------|
| `IMAPNtlmAuthHandler.py` | **ACTIVELY USED** | Used in `thunderbird.py:394-406` for IMAP/NTLM auth |
| `HTTPNtlmAuthHandler.py` | **REMOVED** | Python 2 urllib2-based, never imported anywhere |
| `ntlm.py` | **REQUIRED** | Core NTLM protocol implementation |
| `des*.py`, `U32.py` | **REQUIRED** | Dependencies for ntlm.py |

#### Usage in Codebase

The IMAP NTLM handler is used for Exchange/enterprise email authentication:

```python
# thunderbird.py:394-406
elif "AUTH=NTLM" in imap.capabilities:
    domain = wx.GetTextFromUser(
        _("Please enter the domain for user %s") % self.user
    )
    domain_username = "\\".join([domain.upper(), str(self.user)])
    response, dummy_parameters = imap.authenticate(
        "NTLM",
        IMAPNtlmAuthHandler.IMAPNtlmAuthHandler(domain_username, str(pwd)),
    )
```

#### Why requests-ntlm Is NOT a Replacement

The `requests-ntlm` PyPI package is for HTTP requests using the `requests` library, not for IMAP protocol authentication. The `IMAPNtlmAuthHandler` is purpose-built for Python's `imaplib.IMAP4.authenticate()` method and must be retained.

#### Action Taken

- **Removed:** `HTTPNtlmAuthHandler.py` (138 lines of dead Python 2 code using `urllib2`)
- **Kept:** All other files (required for IMAP authentication)
- **Updated:** `thirdparty/README.txt` to document the removal

#### Potential Future Work

The remaining ntlm module files contain some Python 2 patterns that could be modernized:
- Print statements (though most are commented out)
- String handling (`basestring` references)

However, since the code works and is only used for IMAP authentication, these are low priority.

### deltaTime.py Module

**Date Updated:** November 2025
**Location:** `taskcoachlib/thirdparty/deltaTime.py`
**Source:** https://github.com/pyparsing/pyparsing/blob/master/examples/delta_time.py

#### Background

The `deltaTime.py` module provides natural language time parsing for the task templates feature. It parses expressions like "noon tomorrow", "in 2 hours", "next Monday at 3pm" and converts them to Python datetime objects.

#### Analysis Results

| Attribute | Old Bundled Version | New Upstream Version |
|-----------|---------------------|----------------------|
| **Copyright** | 2010 by Paul McGuire | 2010, 2019 by Paul McGuire |
| **Last Updated** | ~2010 (14 years old) | December 2024 |
| **Export Name** | `nlTimeExpression` | `time_expression` (alias added for compatibility) |
| **pyparsing API** | Old style (`from pyparsing import *`) | Modern (`import pyparsing as pp`) |
| **Local Patches** | Extensive hacks for pyparsing compat | None needed |

#### Problems with Old Version

The bundled 2010 version had extensive local patches to work around pyparsing API changes:

```python
# Lines 72-147 were full of workarounds like:
# "In newer pyparsing, absTime might not be accessible reliably"
# "In newer pyparsing, Group results might be lists, not objects with attributes"
```

These patches made the code fragile and hard to maintain.

#### Usage in Codebase

The module is used **only for the task templates feature**:

| File | Line | Usage |
|------|------|-------|
| `taskcoachlib/gui/dialog/templates.py` | 41 | UI validation of time expressions |
| `taskcoachlib/persistence/xml/reader.py` | 851 | Parsing template times from XML |

#### Action Taken

1. **Replaced** with upstream version from pyparsing examples (December 2024)
2. **Added backward compatibility alias**: `nlTimeExpression = time_expression`
3. **Bumped pyparsing requirement** from `>=3.1.2` to `>=3.1.3` (needed for `pp.Tag`)
4. **Updated install script** to pip install pyparsing (Debian Bookworm only has 3.0.9)

#### New Features in Upstream Version

The upstream version adds capabilities not in the old bundled version:

| Feature | Example |
|---------|---------|
| Word-based numbers | "twenty-four hours from now" |
| Adverbs | "in just 10 seconds", "only a couple of days ago" |
| Complex expressions | "in 3 days at 5pm", "8am the day after tomorrow" |
| Bug fixes | Day-of-week calculations fixed |

#### pyparsing Version Requirement

The upstream `delta_time.py` uses `pp.Tag()` which was added in pyparsing 3.1.3:

```python
time_ref_present = pp.Tag("time_ref_present")
```

**Version availability:**
- Debian Bookworm apt: pyparsing 3.0.9 (too old)
- Required: pyparsing >= 3.1.3
- Solution: Install via pip in virtualenv

#### Files Modified

| File | Change |
|------|--------|
| `taskcoachlib/thirdparty/deltaTime.py` | Replaced with upstream (Dec 2024) |
| `setup.py` | `pyparsing>=3.1.2` → `pyparsing>=3.1.3` |
| `setup_bookworm.sh` | Added `pyparsing>=3.1.3` to pip install |
| `DEBIAN_BOOKWORM_SETUP.md` | Added note about pyparsing needing pip |

### squaremap/ Module

**Date Updated:** November 2025
**Location:** `taskcoachlib/thirdparty/squaremap/` (removed)
**Status:** **REPLACED WITH PyPI DEPENDENCY**

#### Background

SquareMap is a hierarchic data visualization widget for wxPython that displays nested box trees (treemap visualization). Task Coach uses it for effort visualization in the "Square Map" viewer.

#### Analysis Results

| Attribute | Bundled Version | PyPI Version |
|-----------|-----------------|--------------|
| **Version** | 1.0.5 | 1.0.5 |
| **Functional Differences** | None | None |
| **Code Differences** | Black-formatted (double quotes) | Original (single quotes) |

The bundled version was **functionally identical** to PyPI version 1.0.5. The only differences were cosmetic formatting changes applied by the project's Black formatter (double quotes vs single quotes, line wrapping).

#### Why Vendoring Was Unnecessary

The library was vendored (copied into the codebase) as a historical pattern from before pip/virtualenvs were reliable. Since the code is identical to PyPI, there was no reason to maintain a local copy.

#### Action Taken

1. **Removed** `taskcoachlib/thirdparty/squaremap/` directory
2. **Added** `squaremap>=1.0.5` to `install_requires` in `setup.py`
3. **Updated** import in `tcsquaremap.py` from `from ..thirdparty.squaremap import squaremap` to `from squaremap import squaremap`
4. **Updated** `setup_bookworm.sh` to include `squaremap` in pip install list

#### Benefits

- **Automatic updates**: Future bug fixes from PyPI are automatically available
- **Reduced codebase**: Removed ~700 lines of vendored code
- **Standard dependency management**: Uses pip like all other dependencies
- **Cleaner imports**: Standard import path instead of internal thirdparty path

#### Files Modified

| File | Change |
|------|--------|
| `taskcoachlib/thirdparty/squaremap/` | Removed directory |
| `setup.py` | Added `squaremap>=1.0.5` dependency |
| `taskcoachlib/widgets/tcsquaremap.py` | Updated import path, added `FontForLabels` override |
| `setup_bookworm.sh` | Added `squaremap` to pip install list |

#### PyPI squaremap Bug Workaround

The PyPI squaremap 1.0.5 package has a bug in `FontForLabels()` where it passes a float to `Font.SetPointSize()` which requires an int:

```python
# Bug in squaremap 1.0.5:
font.SetPointSize(scale * font.GetPointSize())  # float!

# Fix (in TcSquareMap override):
font.SetPointSize(int(scale * font.GetPointSize()))  # int
```

The `TcSquareMap` class overrides `FontForLabels()` to work around this bug until it's fixed upstream.

---

### snarl.py Module

**Date Removed:** November 2025
**Location:** `taskcoachlib/thirdparty/snarl.py` (removed)
**Status:** **REMOVED**

#### Background

Snarl was a third-party notification system for Windows, popular in the late 2000s/early 2010s (similar to Growl on Mac). Task Coach included Python bindings to integrate with Snarl for desktop notifications.

#### Issues Identified

- Uses deprecated `array.tostring()` (removed in Python 3.13)
- Uses deprecated `inspect.getargspec()`
- No maintained upstream (original author unreachable)
- Snarl itself is essentially abandoned (minimal development since ~2015)
- Windows 10+ has native toast notifications that supersede Snarl
- Very few users have Snarl installed

#### Why Removal is Safe

Task Coach already has a **built-in fallback notification system** (`UniversalNotifier` in `notifier_universal.py`) that:
- Works on all platforms (Windows, Mac, Linux)
- Uses wxPython to create custom notification popup windows
- Provides the same functionality (title, message, icon, timeout)

The notification selection logic in `notifier.py` was:
```python
elif operating_system.isWindows():
    return klass.get("Snarl") or klass.get("Task Coach")
```

With Snarl removed, Windows users automatically get the "Task Coach" (UniversalNotifier) notifications, which work identically.

#### Files Removed

| File | Description |
|------|-------------|
| `taskcoachlib/thirdparty/snarl.py` | Python Snarl bindings (256 lines) |
| `taskcoachlib/notify/notifier_windows.py` | SnarlNotifier class (50 lines) |

#### Other Updates

- `COPYRIGHT.txt` - Removed snarl.py reference

---

## Twisted Framework Removal

**Date Completed:** November 2024
**Affected Components:** Core event loop, Scheduler, File monitoring, iPhone sync
**Root Cause:** Legacy complexity from pre-asyncio era causing subtle bugs

### Background

Task Coach historically used the Twisted framework for asynchronous operations. This was a reasonable choice in the 2004-2010 era when:
- Python had no `async/await` (added in Python 3.5, 2015)
- wxPython's async support was limited
- Twisted was the only mature async framework
- iPhone sync was a major feature (pre-iCloud era)

### Why Twisted Was Removed

1. **Two event loops = subtle bugs**: The `wxreactor` bridged Twisted + wxPython, creating race conditions like shutdown issues
2. **Modern alternatives exist**: wx.CallLater(), asyncio, watchdog, socketserver
3. **Complexity without benefit**: For a desktop GUI app, wx's native event loop is sufficient
4. **Maintenance burden**: Twisted is a large dependency with its own learning curve

### Migration Summary

| Original (Twisted) | Replacement | Location |
|-------------------|-------------|----------|
| `wxreactor.install()` + `reactor.run()` | `wx.App.MainLoop()` | application.py |
| `reactor.callLater(seconds, fn)` | `wx.CallLater(milliseconds, fn)` | scheduler.py |
| `twisted.internet.inotify.INotify` | `watchdog` library | fs_inotify.py |
| `deferToThread()` + `@inlineCallbacks` | `concurrent.futures.ThreadPoolExecutor` | viewer/task.py |
| `twisted.internet.defer.Deferred` | Custom `AsyncResult` class | bonjour.py |
| `twisted.internet.protocol.Protocol` | `socketserver.BaseRequestHandler` | protocol.py |
| `twisted.internet.protocol.ServerFactory` | `socketserver.ThreadingTCPServer` | protocol.py |
| `reactor.listenTCP()` | `ThreadingTCPServer` in background thread | protocol.py |

### Detailed Changes

#### 1. Application Event Loop (application.py)

**Before:**
```python
from twisted.internet import wxreactor
wxreactor.install()
# ... later ...
from twisted.internet import reactor
reactor.registerWxApp(self.__wx_app)
reactor.run()
```

**After:**
```python
# No special initialization needed
self.__wx_app.MainLoop()
```

The wxreactor was a bridge that allowed Twisted's reactor to coexist with wxPython's event loop. This is no longer needed since we use wx's native event loop exclusively.

#### 2. Task Scheduling (scheduler.py)

**Before:**
```python
from twisted.internet import reactor
self.__nextCall = reactor.callLater(nextDuration / 1000, self.__callback)
# Cancel with:
self.__nextCall.cancel()
```

**After:**
```python
import wx
self.__nextCall = wx.CallLater(nextDuration, self.__callback)
# Cancel with:
self.__nextCall.Stop()
```

**Important differences:**
- `reactor.callLater()` takes **seconds** (float)
- `wx.CallLater()` takes **milliseconds** (int)
- Cancel method: `.cancel()` → `.Stop()`

#### 3. File System Monitoring (fs_inotify.py)

**Before:**
```python
from twisted.internet.inotify import INotify
from twisted.python.filepath import FilePath

self.notifier = INotify()
self.notifier.startReading()
self.notifier.watch(FilePath(path), callbacks=[self.onChange])
```

**After:**
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class TaskFileEventHandler(FileSystemEventHandler):
    def on_modified(self, event):
        wx.CallAfter(self.notifier.onFileChanged)

self._observer = Observer()
self._observer.schedule(handler, path, recursive=False)
self._observer.start()
```

**Benefits of watchdog:**
- Cross-platform (Linux inotify, macOS FSEvents, Windows ReadDirectoryChangesW)
- Pure Python, no Twisted reactor integration needed
- Active maintenance and community

#### 4. Background Threading (viewer/task.py)

**Before:**
```python
from twisted.internet.threads import deferToThread
from twisted.internet.defer import inlineCallbacks

@inlineCallbacks
def _refresh(self):
    yield deferToThread(igraph.plot, graph, filename, **style)
    # GUI update code here
```

**After:**
```python
from concurrent.futures import ThreadPoolExecutor

def _refresh(self):
    executor = ThreadPoolExecutor(max_workers=1)

    def do_plot():
        igraph.plot(graph, filename, **style)

    def on_complete(future):
        wx.CallAfter(update_gui)

    future = executor.submit(do_plot)
    future.add_done_callback(on_complete)
```

**Key pattern:** Always use `wx.CallAfter()` to update GUI from background threads.

#### 5. Async Results (bonjour.py)

**Before:**
```python
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure

d = Deferred()
d.callback(result)  # Success
d.errback(Failure(error))  # Error
return d
```

**After:**
```python
class AsyncResult:
    def __init__(self):
        self._callbacks = []
        self._errbacks = []

    def addCallback(self, cb): ...
    def addErrback(self, eb): ...
    def callback(self, result): ...
    def errback(self, error): ...

d = AsyncResult()
d.callback(result)  # Success
d.errback(error)  # Error (plain Exception, not Failure)
return d
```

#### 6. Network Protocol (protocol.py)

**Before:**
```python
from twisted.internet.protocol import Protocol, ServerFactory
from twisted.internet import reactor

class IPhoneHandler(Protocol):
    def connectionMade(self): ...
    def dataReceived(self, data): ...
    def connectionLost(self, reason): ...

class IPhoneAcceptor(ServerFactory):
    protocol = IPhoneHandler

    def __init__(self, ...):
        self.__listening = reactor.listenTCP(port, self)
```

**After:**
```python
import socketserver
import threading

class IPhoneHandler:
    def __init__(self, sock, ...):
        self.transport = SocketTransport(sock)

    def handle(self):
        self.connectionMade()
        while not closed:
            data = sock.recv(4096)
            self.dataReceived(data)
        self.connectionLost(None)

class IPhoneRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        handler = IPhoneHandler(self.request, ...)
        handler.handle()

class IPhoneAcceptor:
    def __init__(self, ...):
        self._server = socketserver.ThreadingTCPServer(('', port), IPhoneRequestHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
```

### Testing Changes

Tests that used `reactor.iterate()` to pump the event loop now use wx event processing:

**Before:**
```python
from twisted.internet import reactor
while time.time() - t0 < 2.0:
    reactor.iterate()
```

**After:**
```python
while time.time() - t0 < 2.0:
    wx.GetApp().Yield(True)
    time.sleep(0.05)  # Prevent CPU spin
```

The `@test.skipOnTwistedVersions()` decorator is now a no-op but kept for backward compatibility.

### Dependencies

**Removed:**
- `twisted` - The Twisted framework

**Added:**
- `watchdog>=3.0.0` - Cross-platform file system monitoring

**Already Present (unchanged):**
- `zeroconf>=0.50.0` - For Bonjour/mDNS service discovery (iPhone sync)

### Code Locations with Design Notes

All modified files contain `DESIGN NOTE (Twisted Removal - 2024):` comments explaining:
- What the original Twisted code did
- Why the replacement was chosen
- Any compatibility considerations

Search for these notes:
```bash
grep -r "DESIGN NOTE (Twisted Removal" taskcoachlib/
```

### Potential Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| `wx.CallLater` not firing | wx event loop not running | Ensure `MainLoop()` is running, or use `wx.GetApp().Yield()` in tests |
| GUI updates from background threads | wxPython is not thread-safe | Always wrap GUI updates in `wx.CallAfter()` |
| Socket server not accepting connections | Server thread not started | Check that `serve_forever()` is running in a daemon thread |

---

## Window Position Tracking with AUI

**Date Fixed:** November 2025
**Affected Components:** WindowDimensionsTracker, MainWindow
**Root Cause:** Multiple sources of spurious resize/move events during initialization

> **See also:** [WINDOW_POSITION_PERSISTENCE_ANALYSIS.md](WINDOW_POSITION_PERSISTENCE_ANALYSIS.md) for detailed analysis of GTK/Linux window positioning, including the `GDK_HINT_USER_POS` issue and the EVT_MOVE + EVT_ACTIVATE solution.

### Problem Overview

After removing Twisted, the main window was not remembering its position and size across restarts. Debug logging revealed that the correct position was loaded from settings, but then immediately overwritten by spurious values.

### Symptoms

1. Window position resets to default on every startup
2. Debug logs show position being saved as incorrect values like `(80, 0)` or size `(6, 28)`
3. Position is correctly loaded but immediately overwritten
4. GTK-CRITICAL errors during startup: `gtk_distribute_natural_allocation: assertion 'extra_space >= 0' failed`

### Root Cause Analysis

There are **two sources** of spurious resize/move events during window initialization:

**Source 1: AUI LoadPerspective()**
The AUI manager causes many resize/move events when restoring pane layout:

```
MainWindow.__init__:
  Line 81: WindowDimensionsTracker created
  Line 231: __restore_perspective() → LoadPerspective() triggers spurious resize/move events
```

**Source 2: GTK Window Realization during Show()**
When `mainwindow.Show()` is called in `Application.start()`, GTK window realization triggers:
- GTK-CRITICAL assertion failure
- Spurious events with invalid values like size=(6, 28) position=(80, 0)

Debug log showing the problem:
```
[23:27:32] __set_dimensions: LOADED pos=(385, 154) size=(875, 539)  ← Correct!
[23:27:32] start_tracking: Binding event handlers
... (resize events during AUI layout)
(taskcoach.py): Gtk-CRITICAL **: gtk_distribute_natural_allocation: assertion failed
[23:27:32] on_change_size: SAVING (6, 28)  ← GTK spurious event!
[23:27:32] on_change_position: SAVING (80, 0)  ← GTK spurious event!
```

### Incorrect Fixes

**Fix Attempt 1: Timer-Based Delay (Hacky)**
```python
# WRONG - hacky timer-based fix
def __init__(self, ...):
    self._initializing = True
    wx.CallLater(500, self._end_initialization)  # Magic number!
```
**Why wrong:** Magic number, not deterministic, doesn't address root cause.

**Fix Attempt 2: Call start_tracking() after LoadPerspective()**
```python
# INSUFFICIENT - spurious events still happen during Show()
def __init_window_components(self):
    self.__restore_perspective()
    self.__dimensions_tracker.start_tracking()  # Too early!
```
**Why insufficient:** `mainwindow.Show()` is called later in `Application.start()`, and GTK realization during Show() triggers more spurious events AFTER start_tracking() was called.

### Correct Fix: Save Only on Close

The simplest and most robust solution: **don't try to save on every resize/move event**.

**Root Cause Analysis:**

There's no reliable way to distinguish "user-initiated" resize/move events from "system-initiated" events in wxWidgets/GTK. The spurious events come from:

1. **Internal code:**
   - `SendSizeEvent()` in `showStatusBar()`, toolbar changes
   - AUI `LoadPerspective()` during layout restoration
   - Various widget updates

2. **System/GTK:**
   - GTK window realization sends configure events asynchronously
   - Window manager placement events

**The Solution: Save Only on Close**

```python
class WindowSizeAndPositionTracker:
    """
    DESIGN NOTE: Save only on close.

    Previously, we tried to save position/size on every EVT_MOVE/EVT_SIZE event.
    This caused problems because GTK and our own code generate many spurious
    resize/move events during window initialization.

    SOLUTION: Only save window state when the window is closed.
    - Simpler implementation (no event handlers for saving)
    - No spurious saves during initialization
    - Only saves the final stable state the user intended
    - Uses the existing save_position() method called on EVT_CLOSE
    """

    def __init__(self, window, settings, section):
        self._is_maximized = False
        self.__set_dimensions()
        # Only track maximize state - position/size saved on close
        self._window.Bind(wx.EVT_MAXIMIZE, self._on_maximize)

    def _on_maximize(self, event):
        """Track maximize state changes."""
        self._is_maximized = True
        event.Skip()

    def save_position(self):
        """Save the position of the window. Called when window is about to close."""
        iconized = self._window.IsIconized()
        if not iconized:
            self.set_setting("position", self._window.GetPosition())
            if not self._window.IsMaximized():
                self.set_setting("size", self._window.GetSize())
        self.set_setting("maximized", self._window.IsMaximized() or self._is_maximized)
```

**Why This Works:**

1. **No spurious saves**: By not binding EVT_MOVE/EVT_SIZE for saving, all spurious events are simply ignored.

2. **Simpler code**: No debouncing, no timers, no event deferral - just save on close.

3. **User intent**: Only saves the final state when the user deliberately closes the window.

4. **Already implemented**: The `save_position()` method was already being called on EVT_CLOSE.

### Additional Fix: Freeze/Thaw for AUI Flickering

Users reported visible flickering during startup as AUI panes were repositioned. This is fixed by wrapping initialization in Freeze/Thaw:

```python
# In mainwindow.py
def _create_window_components(self):
    self.Freeze()  # Prevent flickering during viewer creation
    try:
        self._create_viewer_container()
        viewer.addViewers(...)
        self._create_status_bar()
        self.__create_menu_bar()
    finally:
        self.Thaw()

def __init_window_components(self):
    self.Freeze()  # Prevent flickering during AUI layout
    try:
        self.showToolBar(...)
        self.__restore_perspective()
    finally:
        self.Thaw()
    # Window tracking saves only on close - no special handling needed
```

### Key Learnings

1. **Question the approach first**: The original code tried to save on every EVT_MOVE/EVT_SIZE. The right question was: "Why are we doing this at all?" Saving only on close is simpler and sufficient.

2. **Identify event sources**: Many "spurious" events come from our own code (SendSizeEvent, LoadPerspective) not just GTK. Understanding the sources helps choose the right solution.

3. **No way to distinguish user vs system events**: wxWidgets/GTK doesn't provide a flag to identify user-initiated resize/move. Don't try to filter what you can't identify.

4. **Simpler is better**: Complex solutions (EVT_IDLE deferral, debouncing) were unnecessary. The existing `save_position()` on close was already the right approach.

5. **Freeze/Thaw for flicker**: Batches visual updates to prevent distracting UI flicker during initialization.

6. **Debug logging is essential**: Without detailed logging, this multi-source bug would have been nearly impossible to diagnose.

### Testing Checklist

- [ ] Start app on monitor 1, move to monitor 2, close and reopen → should remember monitor 2
- [ ] Resize window, close and reopen → should remember size
- [ ] Move window to specific position, close and reopen → should remember position
- [ ] Maximize window, close and reopen → should remember maximized state
- [ ] No visible flickering of AUI panes during startup
- [ ] Debug logs should only show RESTORING on startup and save_position on close

### Files Modified

| File | Change |
|------|--------|
| `windowdimensionstracker.py` | Removed EVT_MOVE/EVT_SIZE handlers; save only on close |
| `mainwindow.py` | Added Freeze/Thaw around viewer creation and AUI layout |

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

- ✅ Widget resizing stuck at large sizes (November 2025)
- ✅ wxPython 4.2.0 category background coloring (Documented in CRITICAL_WXPYTHON_PATCH.md)
- ✅ wx.Timer crash when closing Edit Task/Categories quickly (November 2025)
- ✅ Hacky close delay patches removed after root cause fix (November 2025)
- ✅ Ctrl+C crash with AUI event handler assertion (November 2025)
- ✅ Twisted framework removed, replaced with native wxPython + stdlib (November 2025)
- ✅ Window position not remembered due to AUI + GTK spurious events (November 2025)
- ✅ AUI pane flickering during startup fixed with Freeze/Thaw (November 2025)
- ✅ GTK/Linux window position persistence - WM ignores initial position (November 2025) - See [WINDOW_POSITION_PERSISTENCE_ANALYSIS.md](WINDOW_POSITION_PERSISTENCE_ANALYSIS.md)
- ✅ GTK3 menu scroll arrows on first open (December 2025) - FileMenu refactored to use pub/sub
- ✅ Search box text input invisible in AUI toolbars (December 2025) - Added SetMinSize to SearchCtrl
- ✅ AUI divider drag has no visual feedback (December 2025) - Added AUI_MGR_LIVE_RESIZE, throttling, and deferred column resize
- ✅ GTK BitmapComboBox icon clipping (December 2025) - Oversized control width as workaround
- ✅ Main toolbar flicker on customization (December 2025) - Simplified to use GetBestSize() for automatic height
- ✅ File locking library deprecated (December 2025) - Replaced lockfile with fasteners
- ✅ App icon grouping across platforms (December 2025) - Added WM_CLASS, StartupWMClass, CFBundleIdentifier, AppUserModelID
- ✅ GNOME Wayland app icon shows generic gear (December 2025) - Added g_set_prgname via ctypes before GTK init
- ✅ Python 3.12+ SyntaxWarning for invalid escape sequence (December 2025) - Fixed with raw string in desktop module docstring

---

## Python 3.12+ Escape Sequence Warning

**Date Fixed:** December 2025
**Affected Components:** `taskcoachlib/thirdparty/desktop/__init__.py`
**Root Cause:** Python 3.12+ raises SyntaxWarning for invalid escape sequences in regular strings

### Problem Overview

On Debian Trixie (which uses Python 3.12+), installing Task Coach produced a warning:

```
/usr/lib/python3/dist-packages/taskcoachlib/thirdparty/desktop/__init__.py:61: SyntaxWarning: invalid escape sequence '\ '
  DESKTOP_LAUNCH="my\ opener"             Should run the "my opener" program to
```

### Root Cause Analysis

Python 3.12 introduced stricter handling of escape sequences. The module docstring contained example text with `\ ` (backslash-space) which is not a valid escape sequence:

```python
DESKTOP_LAUNCH="my\ opener"             Should run the "my opener" program to
```

In regular strings (not raw strings), `\ ` is interpreted as an escape sequence attempt but `\ ` has no special meaning, triggering the warning.

### The Fix

Converted the module docstring from a regular string to a raw string:

```python
# BEFORE
"""
Simple desktop integration for Python...
"""

# AFTER
r"""
Simple desktop integration for Python...
"""
```

Raw strings treat backslashes as literal characters, avoiding the warning while preserving the documentation's content.

### Files Modified

| File | Change |
|------|--------|
| `taskcoachlib/thirdparty/desktop/__init__.py` | Changed docstring from `"""` to `r"""` |

### Key Learnings

1. **Python 3.12+ is stricter about escape sequences**: What was silently ignored before now produces warnings.

2. **Docstrings are still strings**: Even documentation strings are parsed for escape sequences. Use raw strings (`r"""..."""`) when documentation contains backslashes.

3. **Test on newer Python versions**: Issues like this only appear on newer Python versions (3.12+).

---

## File Locking: lockfile → fasteners Migration

**Date:** December 2025
**Status:** Complete

### Background

The `lockfile` library used for cooperative file locking was deprecated and unmaintained. It has been replaced with `fasteners`, the officially recommended cross-platform file locking library.

### Key Changes

#### Core Implementation

**Before:**
```python
import lockfile

lock = lockfile.FileLock(filename)
lock.acquire(timeout=10)
# ... use file ...
lock.release()
```

**After:**
```python
import fasteners

lock = fasteners.InterProcessLock(filename + ".lock")
acquired = lock.acquire(blocking=True, timeout=0.1)
if not acquired:
    raise LockTimeout(f"File is locked: {filename}")
# ... use file ...
lock.release()
```

#### Custom Exception Classes

Custom exception classes were added to `taskcoachlib/persistence/taskfile.py`:

```python
class LockTimeout(Exception):
    """Raised when file lock cannot be acquired (another process has it)."""
    pass

class LockFailed(Exception):
    """Raised when file locking fails for other reasons."""
    pass
```

These are exported from `taskcoachlib/persistence/__init__.py` and used by `iocontroller.py`.

### Files Modified

| File | Change |
|------|--------|
| `taskcoachlib/persistence/taskfile.py` | Core locking implementation using fasteners |
| `taskcoachlib/persistence/__init__.py` | Export LockTimeout, LockFailed |
| `taskcoachlib/gui/iocontroller.py` | Use persistence.LockTimeout/LockFailed |
| `setup.py` | Replace lockfile with fasteners>=0.19 |
| `debian/control` | Replace python3-lockfile with python3-fasteners |
| `setup_*.sh` | Update pip install commands |
| `tests/unittests/thirdPartySoftwareTests/LockFileTest.py` | Test fasteners instead of lockfile |

### Why Lock File Pattern (Not flock)

The lock file pattern (existence of `.lock` file indicates lock) was preserved because:
- Works reliably on **network drives** (NFS, SMB) where `flock()` may not work
- Cross-platform compatibility
- Safer for document-oriented applications

### References

- [fasteners documentation](https://fasteners.readthedocs.io/)
- [lockfile deprecation notice](https://pypi.org/project/lockfile/)

---

## App Icon Grouping Across Platforms

**Date:** December 2025
**Status:** Complete

### Background

TaskCoach windows were not grouping properly in taskbars/docks across different operating systems. Each platform has its own mechanism for identifying related windows.

### Platform-Specific Solutions

#### Linux: WM_CLASS (X11)

Set at application startup in `taskcoachlib/application/application.py`:

```python
if operating_system.isGTK():
    self.SetClassName("taskcoach")
```

The `WM_CLASS` property tells the X11 window manager which windows belong together.

#### Linux: GLib prgname (Wayland)

**Important:** On Wayland, GNOME Shell uses `app_id` (derived from GLib's `prgname`) instead of X11's `WM_CLASS` to match running applications to their `.desktop` files.

Set at the very start of `taskcoach.py`, **before** any wxPython/GTK imports:

```python
def _set_wayland_app_id():
    """Set GLib prgname for Wayland app_id matching.

    On Wayland, GNOME Shell uses the app_id (derived from GLib's prgname)
    to match running applications to their .desktop files for proper
    icon display. This must be called BEFORE wxPython imports GTK.
    """
    if sys.platform != "linux":
        return

    try:
        import ctypes

        libglib = ctypes.CDLL("libglib-2.0.so.0")
        g_set_prgname = libglib.g_set_prgname
        g_set_prgname.argtypes = [ctypes.c_char_p]
        g_set_prgname.restype = None
        g_set_prgname(b"taskcoach")

        g_set_application_name = libglib.g_set_application_name
        g_set_application_name.argtypes = [ctypes.c_char_p]
        g_set_application_name.restype = None
        g_set_application_name(b"Task Coach")
    except (OSError, AttributeError):
        pass

# Must be called before wx/GTK imports
_set_wayland_app_id()
```

**Why ctypes instead of PyGObject:**
- Using `gi.repository.GLib` can cause segfaults when combined with wxPython
- ctypes directly calls the C function without importing Python GTK bindings
- Avoids potential conflicts with wxPython's GTK initialization

**Why before wxPython imports:**
- GTK reads the prgname during initialization
- wxPython imports GTK when the `wx` module is loaded
- Setting prgname after GTK init has no effect on app_id

#### Linux: StartupWMClass (Desktop Entry)

Added to `build.in/linux_common/taskcoach.desktop`:

```ini
[Desktop Entry]
...
StartupWMClass=taskcoach
```

This links the desktop entry to both WM_CLASS (X11) and app_id (Wayland) for proper dock/taskbar integration.

#### macOS: CFBundleIdentifier

Set in `pymake.py` for app bundle creation:

```python
"CFBundleIdentifier": "org.taskcoach.TaskCoach"
```

#### Windows: AppUserModelID

Set at application startup in `taskcoachlib/application/application.py`:

```python
if operating_system.isWindows():
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("org.taskcoach.TaskCoach")
```

### Files Modified

| File | Change |
|------|--------|
| `taskcoach.py` | g_set_prgname via ctypes (Wayland) |
| `taskcoachlib/application/application.py` | SetClassName (X11), AppUserModelID (Windows) |
| `build.in/linux_common/taskcoach.desktop` | StartupWMClass=taskcoach |
| `pymake.py` | CFBundleIdentifier for macOS |

### Testing

- **Linux (GNOME/KDE on X11)**: All TaskCoach windows group under single taskbar icon via WM_CLASS
- **Linux (GNOME on Wayland)**: App icon displays correctly in dock via app_id/prgname
- **Windows**: Windows group in taskbar with correct app identity
- **macOS**: Windows group under single Dock icon

### References

- [GTK Wayland app_id documentation](https://docs.gtk.org/gtk3/wayland.html)
- [GNOME Application-Based design](https://wiki.gnome.org/Projects/GnomeShell/ApplicationBased)
- [GTK commit: Use g_get_prgname() for xdg_surface.set_app_id](https://gitlab.gnome.org/GNOME/gtk/-/commit/e1fd87728dd841cf1d71025983107765e395b152)

---

## Future Work

### TODO: Right-Aligned Toolbar Icon Jitter During Sash Drag

**Date Identified:** December 2025
**Status:** Investigation complete, fix deferred to separate branch

#### Root Cause

Right-aligned toolbar icons (after stretch spacer) jitter horizontally during AUI sash drag. Investigation revealed the issue is in the AGW AUI library itself:

- **Tools** are DRAWN by `AuiToolBar.OnPaint()` and undergo `GetToolFitsByIndex()` filtering during resize
- **Controls** (wxWindow children) are POSITIONED by wxWidgets' native layout system and remain stable
- The filtering causes positional mismatch during drag, resulting in visual jitter

This only affects tools added after a stretch spacer. Left-aligned tools and all controls (SearchCtrl, Choice dropdowns) do not jitter.

#### Attempted Workaround (Reverted)

A workaround was attempted using `PlateButton` controls instead of native toolbar tools for icons after the stretch spacer. While this prevented jitter, it introduced new issues:

1. **Toggle buttons (ITEM_CHECK)**: Commands like `ViewerHideTasks_completed`, `ViewerHideTasks_inactive`, and `ResetFilter` are toggle buttons. PlateButton has a `PB_STYLE_TOGGLE` style but:
   - Known wxPython issue: `SetState()` is overridden by mouse actions (see [wxPython discussion](https://discuss.wxpython.org/t/how-to-manually-set-the-toggle-state-of-wxpython-platebutton/28745))
   - `EVT_UPDATE_UI` integration needs work to sync initial toggle state from settings
   - Toggle buttons need proper visual feedback (pressed/unpressed state)

2. **Appearance matching**: PlateButton hover highlight differs from native AuiToolBar tools:
   - Native tools: Light grey square background on hover
   - PlateButton with `PB_STYLE_SQUARE | PB_STYLE_NOBG`: Blue oval highlight

3. **Event forwarding complexity**: PlateButton clicks need to be forwarded as `EVT_MENU` events to maintain compatibility with UICommand binding.

The workaround was reverted - all toolbar buttons now use native AuiToolBar tools.

#### Future Work

- Investigate upstream AGW AUI fix for `GetToolFitsByIndex()` during resize
- Or implement proper PlateButton workaround with:
  - `PB_STYLE_TOGGLE` for visual toggle state
  - `EVT_TOGGLEBUTTON` binding for toggle events
  - Proper `EVT_UPDATE_UI` handling to sync initial state
  - Custom styling to match native toolbar appearance

#### Test Application

A minimal test app exists at `test_aui_toolbar_jitter.py` that reproduces the issue and can be used to test fixes.

---

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

**Last Updated:** December 20, 2025
