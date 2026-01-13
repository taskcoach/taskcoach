# Task Coach TODO

This document tracks planned improvements and known issues to address in future releases.

## Table of Contents

- [Simultaneous Processes and Locking](#simultaneous-processes-and-locking)
- [Configuration Naming Convention](#configuration-naming-convention)
- [Refactoring Save Patterns](#refactoring-save-patterns)
- [Backup Feature Review](#backup-feature-review)
- [Setup/Installation Issues](#setupinstallation-issues)
- [Monkeypatches and Workarounds](#monkeypatches-and-workarounds)
- [Datetime and Timezone Refactoring](#datetime-and-timezone-refactoring)
- [Text-to-Speech Modernization](#text-to-speech-modernization)
- [Other TODOs](#other-todos)

---

## Simultaneous Processes and Locking

### Current Status

| Resource | Locking | Status |
|----------|---------|--------|
| Task files (`.tsk`) | `fasteners.InterProcessLock` | ✅ Safe - uses `filename.tsk.lock` |
| INI file (`taskcoach.ini`) | `fasteners.InterProcessLock` | ✅ Safe - uses `taskcoach.ini.lock` |
| Log file (`taskcoachlog.txt`) | None | ⚠️ Shared between instances |

### TODO: Per-Process Log Files

Currently, all Task Coach instances write to the same `taskcoachlog.txt` file. While append mode is generally atomic, log entries from multiple instances can interleave, making debugging difficult.

**Proposed Solutions:**

1. **INI file setting** - Allow users to specify a custom log file path in settings:
   ```ini
   [file]
   logfile = /path/to/custom/taskcoachlog.txt
   ```

2. **Auto-numbered log files** - Automatically append instance number to log filename:
   - First instance: `taskcoachlog.txt`
   - Second instance: `taskcoachlog-2.txt`
   - Third instance: `taskcoachlog-3.txt`
   - etc.

**Implementation Notes:**
- Would need to detect if log file is already in use by another instance
- Could use `fasteners.InterProcessLock` on the log file to detect conflicts
- Instance number could be determined by trying locks sequentially

---

## Configuration Naming Convention

### Current Status

The INI file settings use a mix of naming conventions (legacy):
- `effort`, `view` - single lowercase words
- `minidletime`, `showsmwarning` - concatenated lowercase (hard to read)
- `sdtcspans_effort` - some use underscores

### New Convention (PEP 8)

**All new settings should use `snake_case` naming convention:**

```ini
[feature]
my_new_setting = True    # New style (PEP 8 snake_case)
showsmwarning = True     # Old style (avoid for new settings)
```

**Rationale:**
- Python PEP 8 recommends `snake_case` for identifiers
- More readable than concatenated lowercase
- Matches modern Python conventions

**Note:** Existing settings should NOT be renamed to avoid breaking user INI files.
The `defaults.py` file has a comment marking where new snake_case settings begin.

---

## Refactoring Save Patterns

### Current Status

The application currently uses a per-change save pattern with debouncing to avoid excessive disk writes.

### Proposed Change

Refactor from **per-change with debounce** to **per-window active/lost-focus** save pattern.

| Aspect | Current (Debounce) | Proposed (Focus-based) |
|--------|-------------------|------------------------|
| Save trigger | Timer after last change | Window loses focus |
| Complexity | Complex timers, debounce logic | Simpler event-based |
| Multi-screen | Complex interactions | Cleaner handling |

**Pros:**
- No need for debounce timers
- Simpler implementation without complex timer management
- Cleaner multi-screen/multi-window interactions

**Cons:**
- Less precise undo log (changes batched per focus session)
- Less granular save points if crash or power failure occurs mid-session
- User must switch focus to trigger save

**Status:** To be reviewed

---

## Backup Feature Review

### Issues to Investigate

The backup/restore feature needs review - testing showed unexpected restore behavior.

**Questions to answer:**

1. **Where is the backup file stored?**
   - Document the backup file location
   - Is it configurable?

2. **How are backup/restore points decided?**
   - What triggers a backup point creation?
   - How many backup points are retained?
   - What is the rotation/cleanup policy?

3. **Is the backup file safe against corruption?**
   - What happens if save/update is interrupted (crash, power failure)?
   - Is there atomic write protection?
   - Are there checksums or integrity verification?

4. **Restore behavior:**
   - Why might restore not return expected data?
   - Is there a mismatch between what's shown and what's restored?

**Status:** Needs investigation and documentation

---

## Setup/Installation Issues

### setup.py Does Not Install Prerequisites

**Problem:** Running `python3 setup.py` on a fresh system fails because required dependencies (setuptools, pip, wxPython) are not installed and setup.py does not handle this.

**Current behavior:**
- `python3 setup.py develop` fails with `ModuleNotFoundError: No module named 'setuptools'`
- Even if setuptools is present, wxPython must be installed separately
- No clear error message guiding users to install prerequisites

**Expected behavior:**
- setup.py should either install prerequisites automatically, or
- Provide clear error messages with installation instructions, or
- README should have complete "from scratch" installation instructions

**Workaround:** Users must manually install system packages:
```bash
# Ubuntu/Debian
sudo apt install python3-pip python3-setuptools python3-wxgtk4.0
```

**TODO:**
- [ ] Add prerequisite checks to setup.py with helpful error messages
- [ ] Update README with complete fresh-install instructions
- [ ] Consider using pyproject.toml for modern Python packaging

---

## Monkeypatches and Workarounds

**Status:** Review periodically to determine if still needed

This section documents workarounds and patches in the codebase that should be regularly reviewed to determine if they are still necessary. As wxPython, GTK, and other dependencies evolve, some of these may become obsolete.

### Active Workarounds

| Location | Workaround | Purpose | Review Notes |
|----------|------------|---------|--------------|
| `taskcoach.py:43-71` | `_set_wayland_app_id()` | Sets GLib program name for Wayland app ID matching | Required for proper Wayland dock integration |
| `taskcoach.py:73-74` | `import workarounds.monkeypatches` | Runtime patches for hypertreelist, inspect.getargspec | Required for wxPython compatibility |
| `taskcoach.py:24-30` | TEE module disabled | Stdout/stderr redirection to log file | Disabled pending further testing |
| `application.py:511-516` | `SetActiveTarget` disabled | wx log redirection to stderr | Disabled pending further testing |
| `application.py:21` | `import workarounds` | Workarounds module | **Now empty** - can be removed |

### Removed Legacy Hacks (January 2026)

The following obsolete workarounds were removed from `taskcoach.py`:

| Workaround | Age | Reason for Removal |
|------------|-----|-------------------|
| `XLIB_SKIP_ARGB_VISUALS=1` | 2010 | Ubuntu 10.10 bug workaround - **may resolve Issue #64 segfault** |
| `mx.DateTime` import | 2012 | Ubuntu 12.04 console message - EOL 2017 |
| `wxversion.select(["2.8-unicode", "3.0"])` | 2008 | Ancient wx 2.8/3.0 selection - obsolete since ~2013 |
| `/usr/share/pyshared` path hack | 2012 | Ubuntu 12.04 Python path - EOL 2017 |

**Note:** Removing `XLIB_SKIP_ARGB_VISUALS=1` may resolve Issue #64 - user testing required to confirm. TEE module remains disabled pending further testing.

### wxPython Patches

| Location | Patch | Purpose |
|----------|-------|---------|
| `apply-wxpython-patch.sh` | `hypertreelist.py` patch | Fixes category row background coloring |

### Recommendations

1. **Empty workarounds module:** The `import workarounds` at `application.py:21` can be removed along with the empty `workarounds.py` module.

2. **Regular review:** Check this section every 6-12 months to clean up obsolete workarounds.

---

## Datetime and Timezone Refactoring

### Current Status

TaskCoach uses **naive (timezone-unaware) datetime objects** throughout the codebase. This was common practice in Python 2 era but is now deprecated - Python 3.12+ emits warnings about naive datetime usage.

### The Problem

The naive datetime approach causes issues on Windows with `pywintypes.Time()`:

1. **pywin32 timezone confusion** ([issue #1760](https://github.com/mhammond/pywin32/issues/1760)): When converting datetime objects, pywin32 has inconsistent timezone handling. Windows FILETIME is always UTC, but the conversion to/from Python datetime uses `mktime` which expects local time.

2. **Symptom**: When passing a naive datetime like `datetime(2026, 1, 8, 11, 33, 0)` to `pywintypes.Time()`, it may interpret it as UTC and convert to local time, causing 11:33 AM to display as 7:33 PM (e.g., 8-hour PST offset).

3. **Python 2 vs 3 differences**: The behavior changed between pywin32 versions ([issue #1355](https://github.com/mhammond/pywin32/issues/1355)), which is why this worked before the Python 3 migration.

### Current Workaround

In `taskcoachlib/render.py`, we bypass `pywintypes.Time()` for time-only formatting on Windows:

```python
# For time-only values on Windows, use Python's strftime directly
# to avoid pywintypes.Time() timezone conversion issues
if is_time_only and operating_system.isWindows():
    return dateTime.strftime("%H:%M")
```

This is a pragmatic fix that avoids a major refactor.

### Proper Long-Term Solution

Migrate TaskCoach to use **timezone-aware datetime objects** throughout:

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo  # Python 3.9+

# Modern approach - always use timezone-aware datetimes
aware_dt = datetime.now(timezone.utc)  # UTC
local_dt = datetime.now(ZoneInfo("America/New_York"))  # Local with zone

# Convert to local for display
display_time = aware_dt.astimezone()  # System local timezone
```

### Refactoring Scope

| Component | Location | Effort |
|-----------|----------|--------|
| `DateTime` class | `taskcoachlib/domain/date/dateandtime.py` | High - Core class used everywhere |
| `Date` class | `taskcoachlib/domain/date/date.py` | Medium |
| `TimeDelta` class | `taskcoachlib/domain/date/timedelta.py` | Low |
| Task file I/O | `taskcoachlib/persistence/` | High - Must handle legacy files |
| Rendering | `taskcoachlib/render.py` | Medium |
| UI controls | `taskcoachlib/widgets/datectrl.py` | Medium |

### Migration Strategy

1. **Add timezone support to DateTime class** - Make it timezone-aware while maintaining backward compatibility
2. **Update file I/O** - Store times in UTC, convert to local for display
3. **Update rendering** - Remove Windows-specific workarounds once datetimes are timezone-aware
4. **Legacy file support** - Assume naive datetimes in old files are local time

### References

- [pywin32 issue #1760 - Datetime timezone issues](https://github.com/mhammond/pywin32/issues/1760)
- [pywin32 issue #1355 - DST differences Python 2 vs 3](https://github.com/mhammond/pywin32/issues/1355)
- [Python datetime documentation](https://docs.python.org/3/library/datetime.html)
- [PEP 495 - Local Time Disambiguation](https://peps.python.org/pep-0495/)

**Status:** Workaround in place. Full refactor is a significant undertaking.

---

## Text-to-Speech Modernization

### Current Status

The "Let the computer say the reminder" feature uses a hand-rolled implementation:
- Mac: subprocess call to `say` command
- Linux: subprocess call to `espeak` command
- Windows: No-op (feature unavailable)

The preference is only shown on Mac/Linux, disabled by default.

### Proposed Change

Replace custom implementation with **pyttsx3** library:

| Aspect | Current | With pyttsx3 |
|--------|---------|--------------|
| Windows | Not supported | SAPI5 (native) |
| macOS | subprocess to `say` | NSSpeechSynthesizer (native) |
| Linux | subprocess to `espeak` | espeak (same) |
| Code lines | ~68 | ~15-20 |
| Dependency | None | pyttsx3 |

### Implementation Details

**Files to change:**

| File | Change |
|------|--------|
| `taskcoachlib/speak/speaker.py` | Replace with pyttsx3 implementation |
| `taskcoachlib/gui/dialog/preferences.py` | Remove OS check, show option on all platforms |
| `taskcoachlib/gui/dialog/reminder.py` | No change - API stays the same |

**New speaker.py implementation:**
```python
import pyttsx3
from taskcoachlib import patterns

class Speaker(metaclass=patterns.Singleton):
    def __init__(self):
        self._engine = pyttsx3.init()

    def say(self, text):
        self._engine.say(text)
        self._engine.runAndWait()
```

**References:**
- [pyttsx3 on PyPI](https://pypi.org/project/pyttsx3/) - Latest version 2.99 (July 2025)
- Supports Python 3.9-3.13
- Works offline, no internet required

**Status:** Ready to implement

---

## Other TODOs

*Add future TODO items here as they are identified.*

---

**Last Updated:** January 2026
