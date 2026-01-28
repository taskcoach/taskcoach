# Task Coach Scheduler Architecture

## Overview

Task Coach uses scheduled/timed events for various features. This document describes the architecture after the 2024 refactoring.

## Architecture

The system uses a single `GlobalTimer` that fires every second and publishes events via pubsub. Components subscribe to the events they need.

### Core Component

**File:** `taskcoachlib/gui/timer.py`

```python
class GlobalTimer:
    """Single 1-second timer that publishes timing events."""

    # Events published:
    # - 'timer.second': Every tick
    # - 'timer.minute': When minute changes
    # - 'timer.date': When date changes (or on first run)
```

### Event Flow

```
Every 1 second (_onTick):
    │
    ├── now = DateTime.now()              # ONCE per tick
    │
    ├── currentDate = (year, month, day)  # Extract from now
    ├── currentMinute = (hour, minute)    # Extract from now
    │
    ├── if lastDate != currentDate:       # First run or date change
    │   └── pub.sendMessage('timer.date', timestamp=now)
    │
    ├── if lastMinute != currentMinute:   # Minute changed
    │   └── pub.sendMessage('timer.minute', timestamp=now)
    │
    └── pub.sendMessage('timer.second', timestamp=now)  # Always
```

### Event Subscribers

| Event | Subscriber | Purpose |
|-------|------------|---------|
| `timer.date` | `TaskFilter` | Re-filter tasks at midnight |
| `timer.date` | `CalendarViewer` | Redraw calendar at midnight |
| `timer.minute` | `MinuteRefresher` | Update "time left" displays |
| `timer.second` | `ReminderController` | Check for due reminders |
| `timer.second` | `TaskbarIcon` | Update tracking tooltip |
| `timer.second` | `Editor` | Update budget/revenue while tracking |

### Component Implementation

| Component | File | How It Uses Timer |
|-----------|------|-------------------|
| ComputeStyles | `gui/timer.py` (instantiated in `gui/mainwindow.py`) | Subscribes to `timer.second`, computes task status transitions and recomputes derived/effective appearance for all domain objects. See `docs/TASK_STATUS.md` |
| Reminder Controller | `gui/remindercontroller.py` | Subscribes to `timer.second`, polls all tasks |
| Task Filter | `domain/task/filter.py` | Subscribes to `timer.date`, calls `reset()` |
| Calendar Viewer | `gui/viewer/task.py` | Subscribes to `timer.date`, calls refresh |
| Minute Refresher | `gui/viewer/refresher.py` | Subscribes to `timer.minute` |
| Second Refresher | `gui/viewer/refresher.py` | Uses own `wx.Timer` (per-viewer tracking) |
| Taskbar Icon | `gui/taskbaricon.py` | Subscribes to `timer.second` |
| Task Editor | `gui/dialog/editor.py` | Subscribes to `timer.second` when tracking |

---

## ComputeStyles Processing Flow

```
Every second:
  Skip if no task file loaded

  For each category (one at a time):
    Compute derived (source: parent category's effective values)
    Compute effective (override or derived, with system default)

  For each task (one at a time):
    Compute status (from dates + current time → fires statusChanged if changed)
    Compute derived (sources: categories → parent task → status colors/font/icon)
    Compute effective (override or derived, with system default)

  For each note (one at a time):
    Compute derived (source: parent note's effective values)
    Compute effective (override or derived, with system default)

  For each task's attachments (one at a time):
    Compute derived (no sources → always empty)
    Compute effective (override or system default)

  For each note's attachments (one at a time):
    Compute derived (no sources → always empty)
    Compute effective (override or system default)
```

> **Note:** Categories are processed first because tasks read category.effectiveXxx() during their derived step. Each individual object completes all its phases before the next object starts.

---

## Optimizations

### 1. Single Timestamp Per Tick
```python
def _onTick(self, event):
    now = DateTime.now()  # ONCE - expensive system call
    # All subscribers receive the same timestamp
    pub.sendMessage('timer.second', timestamp=now)
```

### 2. Tuple Comparison for Date/Time
```python
currentDate = (now.year, now.month, now.day)
if self._lastDate != currentDate:  # Fast integer comparison
    ...
```

### 3. First-Run Detection via None
```python
self._lastDate = None  # None = first run

if self._lastDate != currentDate:  # True on first run
    self._lastDate = currentDate
    pub.sendMessage('timer.date', timestamp=now)
```

### 4. Shown Reminders Set (O(1) lookup)
```python
self._shownReminders = set()

if task not in self._shownReminders:  # O(1)
    showReminder(task)
    self._shownReminders.add(task)
```

### 5. Timestamp Passed to Subscribers
```python
# Subscribers reuse the timestamp - NO extra DateTime.now() calls
def _onTimerSecond(self, timestamp):
    now = timestamp  # Use passed value
```

---

## Historical Context

### Old Architecture (Removed)

The old system used a custom `Scheduler` class (`domain/date/scheduler.py`) that wrapped `wx.CallLater` to schedule individual jobs at specific times.

**Problems with old system:**
1. **Double unschedule bug**: Jobs removed when fired, but callbacks tried to unschedule again
2. **Job identity mismatch**: `ScheduledMethod.__eq__` compared by function, self, AND id - creating new `ScheduledMethod` with `id=None` didn't match stored jobs
3. **Complex lifecycle**: Required explicit schedule/unschedule with careful job tracking
4. **Crash potential**: Race conditions when dialogs created/destroyed during callbacks

**Removed files:**
- `taskcoachlib/domain/date/scheduler.py` - Deleted entirely (not deprecated as stub)

### Migration (Completed 2024)

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Create GlobalTimer in `gui/timer.py` | Complete |
| Phase 2 | Migrate Reminder Controller to polling | Complete |
| Phase 3 | Remove scheduling from Task status methods | Complete |
| Phase 4 | Migrate midnight processing (filter, viewers) | Complete |
| Phase 5 | Migrate minute/second processing | Complete |
| Phase 6 | Remove old Scheduler code and update tests | Complete |

---

## Benefits of New Architecture

1. **No jobs to track**: Nothing to schedule, unschedule, or lose
2. **No identity issues**: No `ScheduledMethod` equality comparisons
3. **Simple lifecycle**: Timer starts on app start, stops on app close
4. **Predictable**: Just check conditions, no complex event chains
5. **Debuggable**: Easy to log what's being checked each second
6. **Efficient**: Single timestamp, tuple comparisons, pub/sub dispatch

---

## Performance

### Timer Overhead
- 1-second timer: ~1000 ticks per 16 minutes of use
- Each tick: 1 timestamp call + tuple comparisons + pub/sub dispatch
- Minimal CPU impact for typical usage

### Task List Iteration
- Reminder check iterates task list once per second
- For 1000 tasks: ~1000 comparisons per second (trivial)

### Memory
- Old: One `wx.CallLater` per scheduled event (potentially hundreds)
- New: One `wx.Timer` + small state variables

---

## Change Log

| Date | Change |
|------|--------|
| 2026-01-12 | Initial documentation of current architecture and issues |
| 2026-01-12 | Proposed simplified architecture with global timer |
| 2026-01-12 | Created `gui/timer.py` with optimized `GlobalTimer` class |
| 2026-01-12 | Completed migration of all components |
| 2026-01-12 | Removed old `scheduler.py` entirely (no stub) |
| 2026-01-12 | Updated all tests to use new architecture |
| 2026-01-22 | StatusChecker instantiated in mainwindow.py (was dead code) |
| 2026-01-22 | computeStatus() called from recomputeAppearance() for immediate updates |
| 2026-01-27 | StatusChecker merged into ComputeStyles; status computed per-task before derived/effective |
