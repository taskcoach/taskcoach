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
8. [Planned Refactoring](#planned-refactoring)

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
   Attribute on each task, recomputed by `MasterScheduler._process_task()`.
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
| **DATA-based cascades** | Events | Parent/child auto-completion; an open child reopens its completed parent |

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

- `GlobalTimer`: 1-second timer, publishes `timer.second`
  as Publisher events (`patterns.Event`, source is the GlobalTimer, value is
  the tick timestamp), not pypubsub messages. See
  [PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md).
- `MasterScheduler`: Subscribes to `timer.second`; after its processing, sends the Publisher events `scheduler.date` and `scheduler.minute`

### Event Flow

```
Every 1 second (_on_tick):
    │
    ├── now = DateTime.now()              # ONCE per tick
    │
    └── patterns.Event('timer.second', self, now).send()
```

### Event Subscribers

| Event | Subscriber | Purpose |
|-------|------------|---------|
| `timer.second` | `MasterScheduler` | All per-second data processing |
| `scheduler.date` | `ViewFilter` | Re-filter tasks at midnight, with the new day's statuses |
| `scheduler.date` | `CalendarViewer`, `HierarchicalCalendarViewer` | Move to the new day |
| `scheduler.date` | Viewers with columns (`ViewerWithColumns`) | Redraw relative dates ("Today", "Yesterday") |
| `scheduler.minute` | `MinuteRefresher` | Update "time left" displays |
| `scheduler.minute` | `CalendarViewer`, `HierarchicalCalendarViewer` | Move the "now" line |
| `task.reminder.trigger` | `ReminderController` | Show reminder dialog (see [REMINDERS.md](REMINDERS.md)) |
| `timer.second` | `TaskBarIcon` | Blink the icon while tracking, if enabled (local UI) |
| `timer.second` | `BudgetPage` (task editor) | Update budget/revenue while tracking (local UI) |
| `timer.second` | `EffortEditBook` (effort editor) | Update Time Spent while tracking (local UI) |
| `timer.second` | `SecondRefresher` (task and effort viewers) | Refresh tracked items while tracking (local UI) |
| `timer.second` | `AutoSaver` | Retry a failed autosave after a minute (only while one is pending) |
| `timer.second` | `IdleController` | Poll idle time while tracking with the idle notice enabled (see [IDLE.md](IDLE.md)) |
| `timer.second` | `MainWindow` | Catch system light/dark switches wx does not report (see [SETTINGS.md](SETTINGS.md#system-theme-changes)) |

All of these are Publisher events. Date and minute subscribers use
the `scheduler.*` events, which come after that tick's processing. The
first tick sends `scheduler.date` only when the day differs from the
one the viewers were drawn on (Task Coach started just before
midnight).
`SecondRefresher` asks its viewer `needs_second_refresh()` on each
tick: the task viewer only when a time spent, budget left or revenue
column is shown, the hierarchical calendar never (its "now" line moves
on `scheduler.minute`). The calendars draw their "now" line on
`scheduler.minute` instead of a timer of their own.

### Component Implementation

| Component | File | How It Uses Timer |
|-----------|------|-------------------|
| MasterScheduler | `gui/scheduler.py` | Subscribes to `timer.second`, processes all tasks and styles |
| Reminder Controller | `gui/remindercontroller.py` | Subscribes to `task.reminder.trigger` event (see [REMINDERS.md](REMINDERS.md)) |
| View Filter | `domain/task/filter.py` | `ViewFilter` subscribes to `scheduler.date`, calls `reset()` |
| Calendar Viewers | `gui/viewer/task.py` | Subscribe to `scheduler.date` and `scheduler.minute` |
| Minute Refresher | `gui/viewer/refresher.py` | Subscribes to `scheduler.minute` |
| Second Refresher | `gui/viewer/refresher.py` | Subscribes to `timer.second` while the viewer shows tracked items |
| Taskbar Icon | `gui/taskbaricon.py` | Subscribes to `timer.second` (local UI update) |
| Task Editor | `gui/dialog/editor.py` | `BudgetPage` subscribes to `timer.second` when tracking (local UI) |
| Effort Editor | `gui/dialog/editor.py` | `EffortEditBook` subscribes to `timer.second` while the effort is tracked (Time Spent) |
| Idle Controller | `powermgt/idle.py` | `IdleNotifier` (its base) subscribes to `timer.second` while tracking with the idle notice enabled |
| Main Window | `gui/mainwindow.py` | Subscribes to `timer.second` to check the system light/dark state |

### Subscribing to the Tick

Per-second UI updates subscribe to the GlobalTimer tick; they do not
create their own `wx.Timer`:

```python
self.registerObserver(self._on_timer_second, eventType="timer.second")

def _on_timer_second(self, event):
    timestamp = event.value()
```

A private `wx.Timer` owned by a window keeps a raw C++ pointer to that
window. If it is still running when the window is destroyed, the next
tick is dispatched into freed memory and the app crashes natively, with
no Python traceback. The effort editor's Time Spent display did exactly
that when the start time of a tracked effort was edited and the dialog
closed with the title bar X (see [CRASH_GUARD.md](CRASH_GUARD.md)). A
Publisher subscription is held by weak reference and dispatched in
Python. Subscriptions made with `patterns.Observer.registerObserver`
are removed by `removeInstance()`; editor pages call it on
`EVT_WINDOW_DESTROY`, so a subscription cannot outlive its page even
when it is made after the close handler ran. `MasterScheduler`,
`ViewFilter` and `IdleNotifier` register on the Publisher directly and
unsubscribe in `shutdown()`, `detach()` and `pause()`.

A handler that raises is logged and stays subscribed, so the next tick
runs it again; only handlers of deleted wx objects, or whose own code
touched one, are removed (see
[PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md)). While Task Coach is
quitting the Publisher dispatches nothing; a cancelled quit resumes it.

---

## MasterScheduler Processing Flow

```
Every second (_on_second):
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
    send 'scheduler.date'
  if minuteChanged:
    send 'scheduler.minute'
```

Each category, task and note, and each of the two events, runs
isolated (`_run_isolated`): these steps notify listeners (viewers,
reminder dialogs), and one failing listener must not skip the rest of
the tick or keep the date and minute events from being sent. The
Publisher runs each of their subscribers isolated; pypubsub messages
sent during the processing (status changes, reminder triggers) still
stop at their first failing listener. A failure is logged with the
`[SCHEDULER]` prefix, with its traceback the first time and then a
count every 100 repeats.

> **Key Principle:** MasterScheduler handles TIME-based changes (status updates, reminders, styles). Auto-completion cascades are EVENT-driven via `_onCompletionDateTimeChanged` to respect user intent when manually unchecking tasks.

---

## Optimizations

**Reference:** `scheduler.py:GlobalTimer._on_tick()`, `MasterScheduler._on_second()`

1. **Single Timestamp Per Tick**: `DateTime.now()` called once, passed to all subscribers
2. **Tuple Comparison**: MasterScheduler stores date/minute as tuples for fast integer comparison
3. **First-Tick Detection**: `_last_date = None` runs the daily task processing on the first tick
4. **Timestamp Reuse**: Subscribers receive timestamp parameter, no extra `now()` calls

---

## Performance Considerations

If `_on_second()` ever freezes the UI with very large task files:

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

## Planned Refactoring

**Status:** research started 2026-09-25, paused. Goal: do per-second
work only when something is due or has changed, instead of recomputing
every task each second.

### Cost Today

Time of one `MasterScheduler._on_second()`, measured in a scratch copy
of the app under Xvfb with generated files (parents with 9 subtasks,
20 categories, 50 notes):

| Tasks | Median | Max |
|-------|--------|-----|
| 200 | 62 ms | 78 ms |
| 2000 | 246 ms | 498 ms |
| 5000 | 607 ms | 1281 ms |

It runs on the UI thread every second: with 2000 tasks the UI is
blocked a quarter of the time, so typing, scrolling and window
resizing stutter ("Efficient" above holds only for small files).
Profile at 2000 tasks: `computeStyles` 69%, `computeStoredStatus` 17%,
`recomputeLegacyStatus` 8%. Nearly all of it recomputes unchanged
values; the style setters alone create and send about 40,000 `Event`
objects per tick when nothing changed (28% of the tick).

### What Changes With Time

Status is a pure function of the task's dates, now, the due soon hours
and its prerequisites' completion (`Task.compute_status()`). Time
changes it only at known instants:

- planned start (late), actual start (active), due minus due soon hours
  (due soon), due (overdue)
- reminder, including snooze
- midnight (`scheduler.date`) and each minute (`scheduler.minute`)

Styles change with time only through status. Everything else changes
through data: dates, completion, prerequisites, categories, parent,
overrides, tracking, settings, theme.

### Proposed Design

A time queue and a dirty set, processed on the existing 1-second tick:

- **Queue:** a heap of (time, task id, generation). A task's entry is
  its next transition time, computed from its state by one function.
  When the task changes, its generation goes up and a new entry is
  pushed; stale entries are skipped when popped. Midnight and the next
  minute are entries too.
- **Tick:** compare the head with now, O(1) when nothing is due. Due
  entries mark their tasks dirty.
- **Dirty set:** data changes mark objects dirty as well, from one hook
  where attributes change, not from each setter. The tick recomputes
  status, then styles, parents and categories before their children,
  and marks the dependants of every changed effective value (children,
  categorized items, subcategories) until the set is empty. The
  dependencies form a tree plus categories, so this ends; today a
  parent's change can need one tick per level to reach its children.
- **Full rebuild** (all dirty, queue rebuilt) on file load or merge,
  undo and redo, due soon hours, theme or colour setting changes, and a
  clock jump (now before the last tick, or more than a few seconds
  after it, as after a suspend).

Why one queue on the tick, not one timer per event. The two are the
same idea, and it was tried: the scheduler removed in January 2026
kept a sorted job list with one `wx.CallLater` for the next job (see
[Historical Context](#historical-context)). The design above avoids
its failures:

- Entries are keyed by task id and generation, not by bound methods,
  so no unschedule can miss.
- The next time is recomputed from state, never adjusted in each
  setter. The old setters missed cases: tasks loaded from a file bypass
  the setters ([DATETIME_PRESETS.md](DATETIME_PRESETS.md#reminder-scheduling-on-load)).
- No timer of its own, so nothing fires while dialogs are created or
  destroyed, and no timer outlives its owner
  ([CRASH_GUARD.md](CRASH_GUARD.md)).
- Comparing wall-clock time each tick handles suspend and clock
  changes; a relative timer fires at the wrong wall time.
- The queue can be listed and logged.

The risk polling was chosen to avoid
([TASK_STATUS.md](TASK_STATUS.md#computestyles-polling-new-architecture)):
a missed trigger leaves a stale value. Mitigations: mark dirty in one
place, rebuild on the global changes above, and a debug option that
runs the full pass and logs every difference.

Reminders re-trigger every second while due today, and
`ReminderController` deduplicates. With the queue, decide how a
reminder that is still due re-fires after its dialog closes.

### Steps

Each can ship on its own:

1. Quick wins in the current loop: no `Event` when an attribute value
   is unchanged; drop the legacy status (`recomputeLegacyStatus()`,
   `status()`), moving `statusFgColor()`, `statusBgColor()` and
   `statusFont()` to `computedStatus()` (see
   [TASK_STATUS.md](TASK_STATUS.md#migration-path)). The legacy
   recursive colours and icons that `recomputeAppearance()` still
   computes next to the derived and effective styles are the same kind
   of leftover; `Task.onDailyChange()` is an empty placeholder called
   for every task at midnight.
2. One dirty flag: run today's full pass only when something changed or
   a queue entry is due. Same correctness, almost no cost per second.
3. Per-object dirty set with the ordered cascade. Recursive priority
   ([TODO](#todo) 1) fits the same cascade.
4. Reminders, midnight and minute from the queue.

### How It Was Measured

A copy of the app with `_on_second()` wrapped in
`time.perf_counter()` and one tick run under `cProfile`, opened with
generated task files under Xvfb. Repeat after each step with the same
files to compare.

---
