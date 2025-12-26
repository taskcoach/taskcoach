# Task Coach TODO

This document tracks planned improvements and known issues to address in future releases.

## Table of Contents

- [Simultaneous Processes and Locking](#simultaneous-processes-and-locking)
- [Configuration Naming Convention](#configuration-naming-convention)
- [Refactoring Save Patterns](#refactoring-save-patterns)
- [Backup Feature Review](#backup-feature-review)
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

## Other TODOs

*Add future TODO items here as they are identified.*

---

**Last Updated:** December 2025
