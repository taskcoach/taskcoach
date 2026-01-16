# Python 3 Migration Technical Notes - Part 5: Feature Removals (Continued)

This document is part of the Python 3 migration documentation. See [PYTHON3_MIGRATION_INDEX.md](PYTHON3_MIGRATION_INDEX.md) for the complete index.

**Contents:**
- [Mobile Sync Features Removal](#mobile-sync-features-removal)
- [Native Filesystem Monitors: Deleted](#native-filesystem-monitors-deleted)
- [External Notification System Removal (Growl, KNotify)](#external-notification-system-removal-growl-knotify)
- [X11 Session Management Removal](#x11-session-management-removal)
- [macOS Native Extensions Cleanup](#macos-native-extensions-cleanup)
- [Translation System Simplification](#translation-system-simplification)
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

## External Notification System Removal (Growl, KNotify)

**Date Completed:** January 2026
**Affected Components:** `taskcoachlib/notify/`, preferences UI, setup scripts, packaging

### Background

Task Coach had a "Notification system to use for reminders" preference that allowed users to choose between multiple notification backends:
- **Task Coach** (default) - Built-in wxPython notification popups
- **Growl** (macOS/Windows) - Third-party notification system via `gntp` library
- **KNotify** (Linux/KDE) - KDE notification daemon via DCOP protocol

### Why All External Notifiers Were Removed

**All external notification systems are obsolete:**

| System | Status | Why Obsolete |
|--------|--------|--------------|
| **Growl (macOS)** | Dead | Replaced by Apple's Notification Center (2012) |
| **Growl for Windows** | Dead | Project abandoned; website offline |
| **gntp library** | Unmaintained | Last PyPI release: 2016 |
| **KNotify/DCOP** | Dead | DCOP replaced by D-Bus in KDE 4 (2008) |
| **pydcop library** | Unmaintained | No Python 3 support |

### Why Not Add Modern Notification Support?

The built-in **Task Coach universal notifier** is actually superior for task reminders:

| Feature | Task Coach Notifier | Native Notifications |
|---------|---------------------|---------------------|
| **Snooze options** | Yes - interactive dialog | No |
| **Task details** | Full task info visible | Limited to title/body |
| **Open task button** | Yes | No |
| **Works everywhere** | All platforms | Platform-specific |
| **No dependencies** | Uses wxPython | Requires platform libs |

Native OS notifications (libnotify, Windows Toast, macOS Notification Center) are designed for simple "fire and forget" alerts. Task reminders benefit from the interactive snooze dialog.

### Bug Fixed

The Growl code had a latent bug that would crash Task Coach on startup:

```python
# BEFORE - Broken (no try/except around import)
if operating_system.isMac():
    from .notifier_growl import *
# Would crash with ImportError if gntp not installed
```

Rather than fix this bug, all obsolete notification support was removed.

### Removed Files

| File | Description |
|------|-------------|
| `taskcoachlib/notify/notifier_growl.py` | Growl notifier (~80 lines) |
| `taskcoachlib/notify/notifier_knotify.py` | KNotify notifier (~63 lines) |

### Modified Files

| File | Change |
|------|--------|
| `taskcoachlib/gui/dialog/preferences.py` | Removed "Notification system" dropdown, removed `notify` import |
| `taskcoachlib/config/defaults.py` | Removed `notifier` setting from `[feature]` section |
| `taskcoachlib/notify/notifier.py` | Simplified - single notifier instead of registry |
| `taskcoachlib/notify/__init__.py` | Simplified - only imports universal notifier |
| `taskcoachlib/gui/remindercontroller.py` | Simplified - always uses Task Coach dialog |
| `tests/unittests/ConfigTest.py` | Removed notifier-related test |
| `taskcoachlib/application/application.py` | Removed gntp from package availability check |
| `taskcoachlib/help/__init__.py` | Removed Growl/Snarl notification help text |
| `setup.py` | Removed gntp from extras_require |
| Various setup scripts | Removed gntp references |
| `debian/control` | Removed python3-gntp from Suggests |
| GitHub workflows | Removed gntp from pip install |

### Notification System After Removal

Only the **Task Coach universal notifier** remains:
- Cross-platform wxPython popup windows
- Animated fade-in/fade-out
- Interactive snooze options
- Click to open task editor
- No external dependencies

```python
# notify/__init__.py - simplified
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

## macOS Native Extensions Cleanup

**Date Completed:** January 2026
**Affected Components:** `extension/macos/`, `taskcoachlib/powermgt/`, `taskcoachlib/operating_system.py`

### Background

Task Coach included native C extensions for macOS built for Python 2:

```
extension/macos/
├── bin-ia32/          # 32-bit Intel binaries
│   ├── _idle.so       # Idle time detection
│   └── _powermgt.so   # Power state notifications
├── bin-ia64/          # 64-bit Intel binaries
│   ├── _idle.so
│   └── _powermgt.so
└── src/               # C source code
    ├── idlemgt/       # Uses IOKit HIDIdleTime
    └── powermgt/      # Uses IOPMLib power notifications
```

### Why These Extensions Were Removed

**1. Python 2 API - Incompatible with Python 3**

The C code used Python 2 API functions that don't exist in Python 3:

```c
// BEFORE - Python 2 only (broken in Python 3)
PyMODINIT_FUNC init_idle(void) {
    Py_InitModule3("_idle", methods, "idle time");  // ❌ Doesn't exist in Python 3
}

// Python 3 requires:
PyMODINIT_FUNC PyInit__idle(void) {
    return PyModule_Create(&module);  // ✅ Python 3 API
}
```

**2. Intel-only - No Apple Silicon Support**

The binaries were compiled only for Intel architectures (ia32/ia64). Apple Silicon Macs (M1/M2/M3/M4) with ARM64 architecture would:
- Fail to load the extension entirely, or
- Run through Rosetta 2 emulation with performance penalty

**3. Import Would Crash Task Coach**

Because the extensions used Python 2 API, importing them on Python 3 would crash:

```python
# This would cause immediate crash on Python 3
import _idle  # ❌ Fatal error: undefined symbol Py_InitModule3
```

### Solution: Pure Python Replacements

Both features were reimplemented in pure Python using `ctypes` to call macOS frameworks:

#### Idle Time Detection (IOKit)

```python
# taskcoachlib/powermgt/idle.py - MacIdleQuery class
class MacIdleQuery:
    """Query idle time on macOS using IOKit via ctypes."""

    def __init__(self):
        # Load IOKit and CoreFoundation frameworks
        self._iokit = cdll.LoadLibrary(
            '/System/Library/Frameworks/IOKit.framework/IOKit'
        )
        self._cf = cdll.LoadLibrary(
            '/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation'
        )
        # Create CFString for "HIDIdleTime"
        self._idle_key = self._cf.CFStringCreateWithCString(
            None, b"HIDIdleTime", kCFStringEncodingUTF8
        )

    def getIdleSeconds(self):
        # Get IOHIDSystem service
        hid_service = self._iokit.IOServiceGetMatchingService(
            kIOMasterPortDefault,
            self._iokit.IOServiceMatching(b"IOHIDSystem")
        )
        # Get HIDIdleTime property (returns nanoseconds)
        idle_time_ref = self._iokit.IORegistryEntryCreateCFProperty(
            hid_service, self._idle_key, None, 0
        )
        # Convert nanoseconds to seconds
        return idle_ns.value / 1_000_000_000
```

#### Power State Notifications

Power notifications require registering a callback with `IORegisterForSystemPower` and running a `CFRunLoop`, which is complex to implement in pure Python. The macOS implementation now falls back to the base class (no-op):

```python
# taskcoachlib/powermgt/macos.py
from taskcoachlib.powermgt.base import PowerStateMixinBase

class PowerStateMixin(PowerStateMixinBase):
    """macOS power state mixin - uses base implementation."""
    pass
```

This is acceptable because:
- Idle detection is the primary use case (effort tracking)
- Power notifications were only used for pausing idle detection during sleep

### Removed Files

| File | Lines | Description |
|------|-------|-------------|
| `extension/macos/bin-ia32/_idle.so` | — | 32-bit idle detection binary |
| `extension/macos/bin-ia32/_powermgt.so` | — | 32-bit power management binary |
| `extension/macos/bin-ia64/_idle.so` | — | 64-bit idle detection binary |
| `extension/macos/bin-ia64/_powermgt.so` | — | 64-bit power management binary |
| `extension/macos/src/idlemgt/*` | ~280 | C source for idle detection |
| `extension/macos/src/powermgt/*` | ~280 | C source for power management |

**Total removed:** ~560 lines of C code + 4 binary files

### Obsolete macOS Version Checks Removed

The minimum supported macOS is now **macOS 14 (Sonoma)**, released 2023. These old version checks were removed:

| Function | Checked For | Why Removed |
|----------|-------------|-------------|
| `isMacOsXTiger_OrOlder()` | macOS 10.4 (2005) | 19 years obsolete |
| `isMacOsXLion_OrNewer()` | macOS 10.7 (2011) | 13 years obsolete |
| `isMacOsXMountainLion_OrNewer()` | macOS 10.8 (2012) | 12 years obsolete |
| `isMacOsXMavericks_OrNewer()` | macOS 10.9 (2013) | 11 years obsolete |

**New function added:**
```python
def isMacOsSonoma_OrNewer():
    """Check if running on macOS 14 (Sonoma) or newer."""
    if isMac():
        return _platformVersion() >= (23,)  # Darwin 23 = macOS 14
    return False
```

### Dead Code Removed

Code paths that only executed on pre-Mountain Lion macOS were removed:

| File | Removed Code |
|------|-------------|
| `application.py` | `__init_spell_checking()` method and `on_spell_checking()` |
| `preferences.py` | `maccheckspelling` setting in EditorPage |
| `preferences.py` | Simplified taskbar blinking check to `not isMac()` |
| `taskbaricon.py` | Simplified taskbar blinking to `not isMac()` |
| `defaults.py` | Removed `maccheckspelling` setting |

### macOS Version Reference

For Darwin kernel to macOS version mapping, see: [macOS version history](https://en.wikipedia.org/wiki/MacOS_version_history#Releases)

| Darwin | macOS | Codename | Year |
|--------|-------|----------|------|
| 23 | 14 | Sonoma | 2023 |
| 24 | 15 | Sequoia | 2024 |

### Benefits of This Change

1. **Python 3 compatible:** No more crashes from Python 2 C extensions
2. **Apple Silicon support:** Pure Python works on both Intel and ARM64
3. **Simpler maintenance:** No compiled binaries to maintain
4. **Smaller codebase:** ~560 lines of C code removed
5. **Clear minimum version:** macOS 14 (Sonoma) requirement documented

---

## Translation System Simplification

**Date Completed:** January 2026

### Previous Implementation (Build Step Required)

The old system required a build step:

1. `.po` files in `i18n.in/` directory
2. **`i18n.in/make.py`** + **`po2dict.py`** compiled `.po` → `.py` dict modules
3. Generated `.py` files stored in `taskcoachlib/i18n/` (not in repo)
4. Custom **`tools/pygettext.py`** for string extraction (Python 2 only, broken in Python 3)

### New Implementation (No Build Step)

The simplified system loads `.po` files directly at runtime:

1. `.po` files stored in `taskcoachlib/i18n/locales/` (53 languages)
2. **`po2dict.parse()`** loads single `.po` file at startup
3. No compilation step - translations work immediately
4. Standard **`xgettext`** for string extraction (GNU gettext)

### Changes Made

| Change | Description |
|--------|-------------|
| Moved `.po` files | `i18n.in/*.po` → `taskcoachlib/i18n/locales/*.po` |
| Added `po2dict.parse()` | Returns dict directly without writing file |
| Simplified `Translator` | Loads `.po` at startup, no module imports |
| Removed deprecated API | Deleted `importlib.load_source()` usage |
| Deleted `i18n.in/make.py` | Build step no longer needed |
| Deleted `tools/pygettext.py` | Broken in Python 3, use `xgettext` instead |
| Added `isCurrentLocaleOk()` | Check if wx.Locale was set successfully |
| Suppress wx warning | Use `wx.LogNull` to suppress locale popup |
| Preferences UI update | Show locale warning only when needed |

### String Extraction (For Developers)

Use GNU `xgettext` to extract translatable strings:

```bash
# Extract all _("string") calls from Python files
find taskcoachlib -name "*.py" -not -path "*/i18n/locales/*" > /tmp/pyfiles.txt
xgettext --language=Python --keyword=_ --output=i18n.in/messages.pot \
    --from-code=UTF-8 --files-from=/tmp/pyfiles.txt
```

The `messages.pot` template is in `.gitignore` (generated file).

### How Translations Work

1. **Startup**: `Translator` determines language from settings/environment
2. **Load**: `po2dict.parse()` reads single `.po` file into dict
3. **Translate**: `_("string")` does dict lookup, returns original if not found
4. **Locale**: `wx.Locale` set separately for date/time formatting (may fail if not installed)

### Missing Translations

If a translation is missing, the original English text is shown:
```python
def translate(self, string):
    return self.__language.get(string, string)  # Fallback to original
```

### Locale vs Translation

| Aspect | Translation | Locale |
|--------|-------------|--------|
| Source | `.po` files | System installed |
| Failure | Falls back to English | Shows warning in preferences |
| Affects | UI text | Date/time formats |
| Required | Always works | Optional |

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
