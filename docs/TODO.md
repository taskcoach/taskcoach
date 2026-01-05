# Task Coach TODO

This document tracks planned improvements and known issues to address in future releases.

## Table of Contents

- [Simultaneous Processes and Locking](#simultaneous-processes-and-locking)
- [Configuration Naming Convention](#configuration-naming-convention)
- [Refactoring Save Patterns](#refactoring-save-patterns)
- [Backup Feature Review](#backup-feature-review)
- [Setup/Installation Issues](#setupinstallation-issues)
- [SyncML Removal](#syncml-removal)
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
- `syncml`, `iphone` - single lowercase words
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

## SyncML Removal

### Status: COMPLETED (January 2026)

SyncML was a legacy synchronization protocol that was used for syncing with mobile devices and other applications. The feature added significant complexity to the codebase but was rarely used in modern workflows.

**SyncML has been fully removed from the codebase.** The following items were completed:

- [x] Audit all SyncML-related code paths
- [x] Identify dependencies on SyncML functionality
- [x] Remove SyncML code and related UI elements
- [x] Update documentation to reflect removal
- [x] Backwards compatibility: Old task files with syncmlconfig nodes can still be read

### Removed Files/Directories

- `taskcoachlib/syncml/` - Main SyncML implementation (7 Python files)
- `taskcoachlib/widgets/syncmlwarning.py` - SyncML warning dialog
- `taskcoachlib/gui/dialog/syncpreferences.py` - SyncML preferences dialog
- `taskcoachlib/bin.in/` - pysyncml binary modules for Windows/macOS

### Modified Files

- `taskcoachlib/gui/dialog/preferences.py` - Removed SyncML feature toggle
- `taskcoachlib/gui/menu.py` - Removed SyncML menu items
- `taskcoachlib/gui/uicommand/uicommand.py` - Removed SyncML commands
- `taskcoachlib/gui/mainwindow.py` - Removed SyncML warning display
- `taskcoachlib/gui/iocontroller.py` - Removed synchronize method
- `taskcoachlib/config/defaults.py` - Removed SyncML settings
- `taskcoachlib/persistence/taskfile.py` - Removed SyncML config handling
- `taskcoachlib/persistence/xml/reader.py` - Removed SyncML parsing
- `taskcoachlib/persistence/xml/writer.py` - Removed SyncML writing
- `taskcoachlib/widgets/__init__.py` - Removed SyncML import
- `taskcoachlib/help/__init__.py` - Removed SyncML help section

### Rationale

- Simplified codebase maintenance (~2600 lines removed)
- Reduced attack surface and potential bugs
- Modern sync solutions (cloud file sync, Dropbox) have replaced SyncML
- Removed dependency on unmaintained pysyncml/Funambol libraries
- SyncML was not functional on Linux and required unavailable binary dependencies

---

## Other TODOs

*Add future TODO items here as they are identified.*

---

**Last Updated:** January 2026
