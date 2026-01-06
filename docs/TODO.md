# Task Coach TODO

This document tracks planned improvements and known issues to address in future releases.

## Table of Contents

- [Simultaneous Processes and Locking](#simultaneous-processes-and-locking)
- [Configuration Naming Convention](#configuration-naming-convention)
- [Refactoring Save Patterns](#refactoring-save-patterns)
- [Backup Feature Review](#backup-feature-review)
- [Setup/Installation Issues](#setupinstallation-issues)
- [Monkeypatches and Workarounds](#monkeypatches-and-workarounds)
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
| `taskcoach.py:50-71` | `_set_wayland_app_id()` | Sets GLib program name for Wayland app ID matching | Required for proper Wayland dock integration |
| `taskcoach.py:81` | `XLIB_SKIP_ARGB_VISUALS=1` | Ubuntu 10.10 bug workaround | **Likely obsolete** - Ubuntu 10.10 is ancient |
| `application.py:71-73` | TEE module disabled | Issue #64 segfault workaround | Keep until #64 is resolved |
| `application.py:474-484` | `SetActiveTarget` disabled | Issue #64 segfault workaround | Keep until #64 is resolved |
| `application.py:21` | `import workarounds` | Workarounds module | **Now empty** - can be removed |

### Legacy Hacks in taskcoach.py (Candidates for Removal)

These are ancient workarounds that likely serve no purpose on modern systems:

| Lines | Workaround | Age | Review Notes |
|-------|------------|-----|--------------|
| 82-87 | `mx.DateTime` import | 2012 | Prevents console message on Ubuntu 12.04. **Ubuntu 12.04 EOL 2017** |
| 93-99 | `wxversion.select(["2.8-unicode", "3.0"])` | 2008 | Ancient wx version selection. **wx 2.8 obsolete since ~2013** |
| 101-117 | `/usr/share/pyshared` path hack | 2012 | Ubuntu 12.04 Python path workaround. **Ubuntu 12.04 EOL 2017** |

### wxPython Patches

| Location | Patch | Purpose |
|----------|-------|---------|
| `apply-wxpython-patch.sh` | `hypertreelist.py` patch | Fixes category row background coloring |

### Recommendations

1. **Legacy taskcoach.py hacks (lines 82-117):** These workarounds are 12-16 years old and target systems that have been EOL for years. They should be removed after testing on modern systems.

2. **Ubuntu 10.10 workaround (line 81):** Can likely be removed - Ubuntu 10.10 reached EOL in 2012.

3. **Issue #64 workarounds:** Keep until the underlying segfault issue is fully resolved.

4. **Empty workarounds module:** The `import workarounds` at `application.py:21` can be removed along with the empty `workarounds.py` module.

5. **Regular review:** Check this section every 6-12 months to clean up obsolete workarounds.

---

## Other TODOs

*Add future TODO items here as they are identified.*

---

**Last Updated:** January 2026
