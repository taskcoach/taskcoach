# Task Coach Scheduler Architecture

## Table of Contents

- [TODO](#todo)
1. [Overview](#overview)
   - [SSOT Principle: Scheduler vs Events](#ssot-principle-scheduler-vs-events)
2. [Architecture](#architecture)
3. [MasterScheduler Processing Flow](#masterscheduler-processing-flow)
4. [Optimizations](#optimizations)
5. [Performance Considerations](#performance-considerations)
6. [Historical Context](#historical-context)
7. [Benefits of New Architecture](#benefits-of-new-architecture)

---

## TODO

1. **Review: move recursive priority to scheduler.** Currently, recursive
   priority is computed on-demand by `Task.priority(recursive=True)` and
   notifications are triggered inline — the priority callback walks all
   ancestors, and the completion callback explicitly notifies the parent.
   This is a derived value with multiple inputs, similar to stored status,
   and may be better as a scheduler-computed volatile Attribute.

   **Recursive priority rules:**
   - A task's recursive priority = `max(own priority, max of children's
     recursive priorities)`
   - Only non-completed children are included (completed children are
     excluded from the max)
   - The calculation walks the full subtree recursively

   **Inputs that affect recursive priority:**
   - Own priority changes (`setPriority`)
   - Child priority changes (any descendant)
   - Child completion/uncompletion (`setCompletionDateTime`) — completed
     children are excluded from the recursive max
   - Child added/removed (structural change to subtree)

   **Current notification sites:**
   - `_onPriorityChanged` callback: notifies self + all ancestors
   - `_onCompletionDateTimeChanged` callback: notifies parent
     via `event.addSource` on parent

   **Scheduler approach:** store `recursivePriority` as a volatile
   Attribute on each task, recomputed by `ComputeStyles._computeForObject()`.
   The Attribute equality check suppresses notifications when the value
   hasn't changed. Removes cross-concern coupling from completion callback.
   Same 1-second staleness tradeoff as stored status.

   **Natural cascade (no recursive search):** each task computes its
   recursive priority from its own priority and its direct children's
   already-stored recursive priorities — `max(own, max of children's
   stored recursivePriority)`. The scheduler processes all tasks each
   tick, so values propagate upward naturally. No tree walk needed;
   each task only reads its immediate children's stored values.

---

## Overview

Task Coach uses scheduled/timed events for various features. This document describes the architecture after the 2026 refactoring.

### SSOT Principle: Scheduler vs Events

**Critical distinction between scheduler-updated status and action logic:**

| Responsibility | Mechanism | Example |
|----------------|-----------|---------|
| **TIME-based updates** | Scheduler (polling) | Status recomputation, reminders, styles |
| **DATA-based cascades** | Events | Parent/child auto-completion |

**Why this matters:**

During event handlers, `computedStatus()` may be stale (scheduler hasn't run yet). Action methods like `completed()` and `allChildrenCompleted()` must use **direct field checks** (e.g., `completionDateTime() != maxDateTime`), not `computedStatus()`.

- `computedStatus()`: For UI display, filtering, reporting (updated every second by scheduler)
- Direct field checks: For action logic, cascades, event handlers (always current)

See also: `docs/TASK_STATUS.md` section "SSOT Principle: Action vs Display"

---

## Architecture

The system uses a `GlobalTimer` that fires every second, and a `MasterScheduler` that handles all per-second processing. Only MasterScheduler subscribes to `timer.second` for data processing.

### Core Components

**File:** `taskcoachlib/gui/scheduler.py`

- `GlobalTimer`: 1-second timer, publishes `timer.second`, `timer.minute`, `timer.date`
- `MasterScheduler`: Subscribes to `timer.second`, emits `scheduler.dateChange.uiRefresh`, `scheduler.minuteChange.uiRefresh`

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
| `timer.second` | `MasterScheduler` | All per-second data processing |
| `timer.date` | `TaskFilter` | Re-filter tasks at midnight |
| `scheduler.dateChange.uiRefresh` | `CalendarViewer` | Redraw calendar after midnight processing |
| `scheduler.minuteChange.uiRefresh` | `MinuteRefresher` | Update "time left" displays |
| `task.reminder.trigger` | `ReminderController` | Show reminder dialog |
| `timer.second` | `TaskbarIcon` | Update tracking tooltip (local UI) |
| `timer.second` | `Editor` | Update budget/revenue while tracking (local UI) |

### Component Implementation

| Component | File | How It Uses Timer |
|-----------|------|-------------------|
| MasterScheduler | `gui/scheduler.py` | Subscribes to `timer.second`, processes all tasks and styles |
| Reminder Controller | `gui/remindercontroller.py` | Subscribes to `task.reminder.trigger` event |
| Task Filter | `domain/task/filter.py` | Subscribes to `timer.date`, calls `reset()` |
| Calendar Viewer | `gui/viewer/task.py` | Subscribes to `scheduler.dateChange.uiRefresh` |
| Minute Refresher | `gui/viewer/refresher.py` | Subscribes to `scheduler.minuteChange.uiRefresh` |
| Second Refresher | `gui/viewer/refresher.py` | Uses own `wx.Timer` (per-viewer tracking) |
| Taskbar Icon | `gui/taskbaricon.py` | Subscribes to `timer.second` (local UI update) |
| Task Editor | `gui/dialog/editor.py` | Subscribes to `timer.second` when tracking (local UI) |

---

## MasterScheduler Processing Flow

```
Every second (_onSecond):
  Skip if no task file loaded

  Detect date/minute changes

  For each category:
    computeStyles(category)

  For each task:
    if dateChanged: task.onDailyChange()
    task.recomputeLegacyStatus()        # Legacy __status
    task.computeStoredStatus()          # Modern __computed_status
    task.processReminder()              # Fire trigger if due
    computeStyles(task)
    computeStyles(task.notes)
    computeStyles(task.attachments)

  For each global note:
    computeStyles(note)
    computeStyles(note.attachments)

  if dateChanged:
    emit 'scheduler.dateChange.uiRefresh'
  if minuteChanged:
    emit 'scheduler.minuteChange.uiRefresh'
```

> **Key Principle:** MasterScheduler handles TIME-based changes (status updates, reminders, styles). Auto-completion cascades are EVENT-driven via `_onCompletionDateTimeChanged` to respect user intent when manually unchecking tasks.

---

## Optimizations

**Reference:** `scheduler.py:GlobalTimer._onTick()`, `MasterScheduler._onSecond()`

1. **Single Timestamp Per Tick**: `DateTime.now()` called once, passed to all subscribers
2. **Tuple Comparison**: Date/minute stored as tuples for fast integer comparison
3. **First-Run Detection**: `_lastDate = None` triggers date event on first tick
4. **Timestamp Reuse**: Subscribers receive timestamp parameter, no extra `now()` calls

---

## Performance Considerations

If `_onSecond()` ever freezes the UI with very large task files:

1. **Profile first** - Don't optimize blindly. Identify actual bottlenecks before making changes.

2. **Yield to event loop** - If loop iteration is the issue, yield to wx event loop every 100-200ms using `wx.SafeYield()` or `wx.GetApp().Yield()`.

3. **Only if needed** - Only add yielding if there are actual cases where processing exceeds 100-200ms.

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


---

## Benefits of New Architecture

1. **No jobs to track**: Nothing to schedule, unschedule, or lose
2. **No identity issues**: No `ScheduledMethod` equality comparisons
3. **Simple lifecycle**: Timer starts on app start, stops on app close
4. **Predictable**: Just check conditions, no complex event chains
5. **Debuggable**: Easy to log what's being checked each second
6. **Efficient**: Single timestamp, tuple comparisons, pub/sub dispatch

---


