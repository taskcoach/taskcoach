# Python 3 Migration Technical Notes - Part 2: Library Cleanup and Framework Removal

This document is part of the Python 3 migration documentation. See [PYTHON3_MIGRATION_INDEX.md](PYTHON3_MIGRATION_INDEX.md) for the complete index.

**Contents:**
- [Bundled Third-Party Library Cleanup](#bundled-third-party-library-cleanup)
- [Twisted Framework Removal](#twisted-framework-removal)
- [Window Position Tracking with AUI](#window-position-tracking-with-aui)

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

**Previous:** [Part 1: Core wxPython Issues](PYTHON3_MIGRATION_1.md)

**Next:** [Part 3: GTK and AUI Issues](PYTHON3_MIGRATION_3.md)

**Last Updated:** January 2026
