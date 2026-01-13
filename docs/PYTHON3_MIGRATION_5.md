# Python 3 Migration Technical Notes - Part 5: Feature Removals (Continued)

This document is part of the Python 3 migration documentation. See [PYTHON3_MIGRATION_INDEX.md](PYTHON3_MIGRATION_INDEX.md) for the complete index.

**Contents:**
- [Mobile Sync Features Removal](#mobile-sync-features-removal)
- [Native Filesystem Monitors: Deleted](#native-filesystem-monitors-deleted)
- [Growl Notification Support Removal](#growl-notification-support-removal)
- [X11 Session Management Removal](#x11-session-management-removal)
- [Contributing to This Document](#contributing-to-this-document)

---

## Mobile Sync Features Removal

**Date Completed:** January 2026

### Why Mobile Sync Was Removed

**The mobile apps are dead.** Both the iOS app and Android third-party app are no longer available or maintained.

| Platform | Previous Status | Reason for Removal |
|----------|-----------------|-------------------|
| **iOS (iPhone/iPad)** | Had companion app on App Store | App no longer available; last update ~2012-2016 |
| **Android** | Third-party app by Ajiget | Developer site abandoned; app not maintained |
| **SyncML (all)** | Funambol-based sync | Protocol dead; see SyncML Removal section in Part 4 |

### Removed Files/Directories

```
taskcoachlib/iphone/           # iPhone sync implementation
├── __init__.py
├── bonjour.py                 # Zeroconf service discovery
└── protocol.py                # Binary sync protocol (~1800 lines)

taskcoachlib/gui/iphone.py     # Sync progress frame
taskcoachlib/gui/dialog/iphone.py  # Sync type and Bonjour dialogs
```

### Modified Files

| File | Change |
|------|--------|
| `taskcoachlib/gui/mainwindow.py` | Removed Bonjour registration, iPhone sync methods |
| `taskcoachlib/gui/dialog/preferences.py` | Removed IPhonePage preferences |
| `taskcoachlib/config/defaults.py` | Removed `[iphone]` config section and `feature.iphone` |
| `taskcoachlib/application/application.py` | Removed Bonjour cleanup on quit |
| `taskcoachlib/help/__init__.py` | Removed iPhone and Android help sections |
| `setup.py` | Removed `zeroconf` dependency |
| `website.in/make.py` | Removed Android download page and references |
| `website.in/style.py` | Removed Android from download menu |

### Summary Table

| Platform | Status | Notes |
|----------|--------|-------|
| **iOS (iPhone/iPad)** | **Removed** | App no longer available |
| **Android** | **Removed** | Third-party app abandoned |
| **SyncML (all)** | **Removed** | Protocol is dead (see Part 4) |

---

## Native Filesystem Monitors: Deleted

**Date Completed:** January 2026
**Affected Files:** `taskcoachlib/filesystem/`
**Root Cause:** Redundant platform-specific code duplicated functionality provided by watchdog library

### Background

The `taskcoachlib/filesystem/` module monitors `.tsk` task files for external changes. When a file is modified outside Task Coach (e.g., by sync tools, backup software, or manual editing), the application detects the change and prompts the user to reload.

**Original architecture (BEFORE):**
```
taskcoachlib/filesystem/
├── __init__.py      # Platform selector
├── base.py          # Base class
├── fs_darwin.py     # macOS: Native kqueue/kevent (289 lines)
├── fs_win32.py      # Windows: Native ReadDirectoryChangesW (142 lines)
├── fs_inotify.py    # Linux: Used watchdog library
└── fs_poller.py     # Fallback: polling every 10 seconds
```

### Why fs_darwin.py and fs_win32.py Were Redundant

The `watchdog` library (a Python package) already provides cross-platform file monitoring:

- **fs_darwin.py** (289 lines): Implemented native macOS `kqueue`/`kevent` API
  - watchdog already uses FSEvents on macOS (more efficient than kqueue for file monitoring)

- **fs_win32.py** (142 lines): Implemented native Windows `ReadDirectoryChangesW` API
  - watchdog already uses this same API on Windows

- **fs_inotify.py**: Already used watchdog library (despite the name suggesting Linux inotify)
  - watchdog uses inotify on Linux, FSEvents on macOS, ReadDirectoryChangesW on Windows
  - The file was misnamed; it was actually a cross-platform watchdog wrapper

**Key insight:** We were maintaining 431 lines of platform-specific native code that duplicated functionality already provided by our existing dependency.

### Old Platform Selection Code (BEFORE - __init__.py)

```python
import platform

_system = platform.system()

if _system == 'Linux':
    from .fs_inotify import *     # Used watchdog
elif _system == 'Darwin':
    from .fs_darwin import *      # Native kqueue (289 lines)
elif _system == 'Windows':
    from .fs_win32 import *       # Native Win32 API (142 lines)
else:
    from .fs_poller import *      # Polling fallback
```

### New Platform Selection Code (AFTER - __init__.py)

```python
"""
File system monitoring module.

Uses the cross-platform watchdog library for all platforms:
- Linux: inotify
- macOS: FSEvents
- Windows: ReadDirectoryChangesW
- Other: Polling fallback
"""

import logging

from .fs_poller import *

try:
    from .fs_watchdog import *
except ImportError:
    logging.warning(
        "watchdog library not installed. File monitoring will use polling fallback "
        "(less efficient). Install watchdog for better performance: pip install watchdog"
    )

    class FilesystemNotifier(FilesystemPollerNotifier):
        pass
```

### Files Deleted

| File | Lines | Native API | Why Redundant |
|------|-------|------------|---------------|
| `fs_darwin.py` | 289 | kqueue/kevent | watchdog uses FSEvents (more efficient) |
| `fs_win32.py` | 142 | ReadDirectoryChangesW | watchdog uses same API |

**Total code removed:** 431 lines of platform-specific native code

### Files Renamed

| Old Name | New Name | Reason |
|----------|----------|--------|
| `fs_inotify.py` | `fs_watchdog.py` | Reflects actual implementation (cross-platform watchdog) |

### Current Module Structure

```
taskcoachlib/filesystem/
├── __init__.py      # Uses watchdog for all platforms, falls back to polling
├── base.py          # Base class (FilesystemNotifierBase)
├── fs_watchdog.py   # Cross-platform watchdog implementation
└── fs_poller.py     # Fallback polling (if watchdog unavailable)
```

### Watchdog Official Platform Support

Per [PyPI watchdog 6.0.0](https://pypi.org/project/watchdog/) (November 2024):

| Platform | Backend | Notes |
|----------|---------|-------|
| Linux 2.6+ | inotify | Kernel-level file notification |
| macOS | FSEvents | Apple's file system events API |
| Windows | ReadDirectoryChangesW | Win32 native API |
| FreeBSD/BSD | kqueue | BSD kernel events |
| Other | Polling fallback | Automatic fallback |

### Benefits of This Change

1. **Reduced maintenance:** 431 fewer lines of platform-specific code to maintain
2. **Better macOS support:** FSEvents is more efficient than kqueue for file monitoring
3. **Consistent behavior:** Same watchdog library handles all platforms identically
4. **Graceful degradation:** Falls back to polling with a warning if watchdog unavailable
5. **Simpler testing:** Only need to test watchdog wrapper, not three native implementations

---

## Growl Notification Support Removal

**Date Completed:** January 2026
**Affected Components:** `taskcoachlib/notify/`, setup scripts, build workflows, packaging

### Background

Growl was a third-party notification system for macOS (and later Windows via "Growl for Windows"), popular in the 2005-2015 era. Task Coach used the `gntp` (Growl Notification Transport Protocol) library to integrate with Growl for desktop notifications.

### Why It Was Removed

**Growl is dead.** This is the primary reason for removal.

| Aspect | Status |
|--------|--------|
| **Growl for macOS** | Replaced by Apple's built-in Notification Center (macOS 10.8+, 2012) |
| **Growl for Windows** | Project abandoned; website offline |
| **gntp library** | Last PyPI release: 2016; no Python 3.10+ testing |
| **User adoption** | Near zero - native notifications are standard on all platforms |

Modern operating systems have built-in notification systems:
- **macOS**: Notification Center (since 2012)
- **Windows**: Toast notifications (since Windows 8, 2012)
- **Linux**: libnotify / D-Bus notifications

Task Coach already has a **universal notifier** (`notifier_universal.py`) that provides cross-platform notifications using wxPython, making Growl completely redundant.

### Bug Fixed

The Growl code had a latent bug that would crash Task Coach on startup on macOS/Windows if gntp was not installed:

```python
# BEFORE - Broken (no try/except around import)
if operating_system.isMac():
    from .notifier_growl import *

# This would crash with ImportError if gntp not installed
```

Rather than fix this bug, the entire Growl support was removed since the feature is obsolete.

### Removed Files

| File | Description |
|------|-------------|
| `taskcoachlib/notify/notifier_growl.py` | GrowlNotifier class (~80 lines) |

### Modified Files

| File | Change |
|------|--------|
| `taskcoachlib/notify/__init__.py` | Removed Growl imports, simplified to universal notifier only |
| `taskcoachlib/notify/notifier.py` | Removed `operating_system` import, simplified `getSimple()` |
| `taskcoachlib/application/application.py` | Removed gntp from package availability check |
| `taskcoachlib/help/__init__.py` | Removed Growl/Snarl notification help text |
| `taskcoachlib/gui/remindercontroller.py` | Updated comment about notification systems |
| `setup.py` | Removed gntp from extras_require and mac platform installs |
| `setup.sh` | Removed gntp reference |
| `setup_arch.sh` | Removed gntp package |
| `setup_debian12_bookworm.sh` | Removed gntp reference |
| `setup_debian13_trixie.sh` | Removed gntp reference |
| `setup_ubuntu2204_jammy.sh` | Removed gntp reference |
| `setup_ubuntu2404_noble.sh` | Removed gntp reference |
| `build.in/arch/PKGBUILD` | Removed python-gntp dependency |
| `build.in/arch/taskcoach.install` | Removed gntp mention |
| `debian/control` | Removed python3-gntp from Suggests |
| `.github/workflows/build-windows.yml` | Removed gntp from pip install |
| `.github/workflows/build-appimage.yml` | Removed gntp from pip install |
| `scripts/build-appimage.sh` | Removed gntp from pip install |
| `docs/PACKAGING.md` | Removed all gntp references |
| `docs/DEBIAN_BOOKWORM_SETUP.md` | Removed gntp mention |
| `docs/DEBIAN_TRIXIE_PLANNING.md` | Removed gntp mention |

### Notification System After Removal

All platforms now use the **universal notifier** which provides:
- Cross-platform notification popups using wxPython
- Consistent appearance on all platforms
- No external dependencies (uses built-in wx capabilities)
- Timeout and click handling

```python
# notify/__init__.py - simplified
# All platforms now use the universal notifier which provides native notifications.
from .notifier_universal import *
from .notifier import *
```

### See Also

The Snarl notification support (Windows equivalent of Growl) was removed in November 2025. See [Part 2: Bundled Third-Party Library Cleanup](PYTHON3_MIGRATION_2.md#snarlpy-module) for details.

---

## X11 Session Management Removal

**Date Completed:** January 2026
**Affected Components:** `taskcoachlib/powermgt/xsm.py`, `taskcoachlib/gui/dialog/xfce4warning.py`, preferences, config

### Background

X11 Session Management (XSMP) is a protocol that allows applications to integrate with the Linux/Unix desktop session manager. When enabled, Task Coach would connect to the session manager and receive "save yourself" signals before logout/shutdown.

### Why It Was Removed

**The feature was redundant.** Task Coach already handles shutdown gracefully through standard mechanisms:

| Mechanism | Already Implemented |
|-----------|-------------------|
| `SIGTERM` / `SIGINT` | Signal handlers in `application.py` |
| `EVT_QUERY_END_SESSION` | wxPython session event handler |
| `EVT_END_SESSION` | wxPython session event handler |
| `EVT_CLOSE` | Window close event handler |

Modern Linux desktops send `SIGTERM` when logging out or shutting down. The application's existing signal handlers catch this and perform a clean shutdown. The X11 SM protocol added:

- **Extra complexity:** 484 lines of ctypes bindings to `libSM.so` and `libICE.so`
- **A separate thread:** ICE connection polling loop
- **Known bugs:** XFCE4 warning dialog existed because X11 SM caused freezes on XFCE
- **Zero additional functionality:** Everything it did was already handled by SIGTERM

### The XFCE4 Warning

The codebase included a warning dialog specifically for XFCE4 users:

> "If you experience random freeze at startup, please uncheck the 'Use X11 session management' in the Features tab of the preferences."

This warning existed because the X11 SM implementation had bugs that caused freezes on XFCE. Rather than fix these bugs in obsolete code, the entire feature was removed.

### Removed Files

| File | Lines | Description |
|------|-------|-------------|
| `taskcoachlib/powermgt/xsm.py` | 484 | X11 Session Management Protocol implementation |
| `taskcoachlib/gui/dialog/xfce4warning.py` | ~50 | XFCE4 freeze warning dialog |

### Modified Files

| File | Change |
|------|--------|
| `taskcoachlib/gui/dialog/preferences.py` | Removed "Use X11 session management" checkbox |
| `taskcoachlib/config/defaults.py` | Removed `usesm2` and `showsmwarning` settings |
| `taskcoachlib/application/application.py` | Removed `__init_session_monitor()` and `sessionMonitor` |
| `taskcoachlib/gui/mainwindow.py` | Removed `checkXFCE4()` method and XFCE4WarningDialog import |

### How Shutdown Works Now

The application handles shutdown through these standard mechanisms (unchanged):

```python
# application.py - signal handlers
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

# application.py - wxPython session events
self.Bind(wx.EVT_QUERY_END_SESSION, self.onQueryEndSession)

# mainwindow.py - window close
self.Bind(wx.EVT_CLOSE, self.onClose)
```

These work reliably on all platforms without platform-specific session management code.

### Benefits of Removal

1. **Eliminated freeze bugs:** No more XFCE4 startup freezes
2. **Reduced complexity:** 534 fewer lines of platform-specific code
3. **No thread overhead:** Removed ICE polling thread
4. **Simpler preferences:** One less checkbox to confuse users
5. **Cross-platform consistency:** Same shutdown handling on all platforms

---

## Contributing to This Document

When adding new technical notes:

1. Include the date the issue was discovered/fixed
2. Provide before/after code examples
3. Explain the root cause, not just the symptoms
4. Add testing checklists when applicable
5. Link to related issues/PRs when available

---

**Previous:** [Part 4: Infrastructure, i18n, and Feature Removals](PYTHON3_MIGRATION_4.md)

**Last Updated:** January 2026
