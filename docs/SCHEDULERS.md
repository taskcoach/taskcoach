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
8. [The Master Timer List](#the-master-timer-list)

---

## TODO

1. **Decided 2026-09-28: recursive priority stays out of the
   scheduler.** It depends on data only (priorities, completion, the
   tree), never on time, so it goes by events, as it always did
   ([TASK_FIELDS.md](TASK_FIELDS.md#priority)). Computed by
   the loop it would lag a tick behind each edit and climb one level
   per pass, as the loop visits parents first.

---

## Overview

Task Coach uses scheduled/timed events for various features. This document describes the architecture after the 2026 refactoring.

### SSOT Principle: Scheduler vs Events

**Critical distinction between scheduler-updated status and action logic:**

| Responsibility | Mechanism | Example |
|----------------|-----------|---------|
| **TIME-based updates** | Scheduler (master timer list) | Status recomputation, reminders, styles |
| **DATA-based cascades** | Events | Parent/child auto-completion; an open child reopens its completed parent. On edits only: loading or merging a file runs neither ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)) |

**Why this matters:**

During event handlers, `computedStatus()` may be stale (scheduler hasn't run yet). Action methods like `completed()` and `allChildrenCompleted()` must use **direct field checks** (e.g., `completionDateTime() != maxDateTime`), not `computedStatus()`.

- `computedStatus()`: For UI display, filtering, reporting (recomputed on each date change, and by the master loop at the seconds time changes it)
- Direct field checks: For action logic, cascades, event handlers (always current)

See also: `docs/TASK_STATUS.md` section "SSOT Principle: Action vs Display"

---

## Architecture

The system uses a `GlobalTimer` that fires every second, and a
`MasterScheduler` that keeps the master timer list and, at the seconds
it holds or after a change, processes the objects concerned and what
reads them
([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#incremental-pass)). Only
MasterScheduler subscribes to `timer.second` for data processing.

### Core Components

**File:** `taskcoachlib/gui/scheduler.py`

- `GlobalTimer`: 1-second timer, publishes `timer.second`
  as Publisher events (`patterns.Event`, source is the GlobalTimer, value is
  the tick timestamp). See
  [PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md).
- `MasterScheduler`: Subscribes to `timer.second`; sends the Publisher events `scheduler.aboutToPass` and `scheduler.pass` around a pass, then `scheduler.date` and `scheduler.minute`

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
| `timer.second` | `MasterScheduler` | The master timer list check; a pass when an entry is due or an object marked |
| `scheduler.pass` | Task `Sorter`, `ViewFilter` | Re-sort and refilter once by the statuses the pass changed |
| `scheduler.aboutToPass`, `scheduler.pass` | Viewers (`Viewer`) | Gather the items the pass changes, refresh their rows once after it, as after a bulk command ([P140](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues)) |
| `scheduler.aboutToPass`, `scheduler.pass` | Tray icon (`_OnceAfterBursts`) | Count the statuses for the tool tip once after the pass, as after a bulk command ([P145](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues)) |
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
| MasterScheduler | `gui/scheduler.py` | Subscribes to `timer.second`; runs a pass when the master timer list holds a due entry or an object is marked |
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
create their own `wx.Timer`. Anything finer or not tied to the clock
(a debounce, a short delay, an animation) goes through `patterns.later`
([DEFERRED_CALLS.md](DEFERRED_CALLS.md)):

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
`ViewFilter` and `IdleNotifier` register on the Publisher directly; a
filter unsubscribes when its viewer closes (`detach()`), the idle
notifier when tracking stops (`pause()`). Nothing unsubscribes at quit
([DEFERRED_CALLS.md](DEFERRED_CALLS.md), lazy teardown): the
per-second tick ends with the main window. `MasterScheduler.shutdown()`
serves tests, whose schedulers outlive them.

A handler that raises is logged and stays subscribed, so the next tick
runs it again; only handlers of deleted wx objects, or whose own code
touched one, are removed (see
[PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md)). While Task Coach is
quitting the Publisher dispatches nothing; a cancelled quit resumes it.

---

## MasterScheduler Processing Flow

The master timer list holds, sorted, each task's seconds at which time
alone changes it (`Task.timer_seconds()`, one per rule; a date not set
has none), each entry with its task and rule; a date change replaces
the task's entries, a deletion removes them. A change the passes read
marks the objects it concerns as its event arrives. Its design,
rulings and coverage are in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#incremental-pass).

```
Every second (_on_second):
  Skip if no task file loaded
  A tick earlier than the last one (clock set back): rebuild the list,
  and the full loop

  Detect minute changes

  The entries up to now (past ones and this second's) mark their
  tasks and leave the list. Then one pass, after
  'scheduler.aboutToPass':
    The full loop, if due: every object
    Otherwise: the marked objects and what reads a style they change
      (a category's subcategories and members, a parent's children)
  each object once, categories, tasks, notes, attachments, parents
  first:
    A task in the file:
      task.compute_stored_status(tick)      # The status at the tick
      task.processReminder(tick)            # Fire trigger if due
      computeStyles(task)
    A category, note or attachment:
      computeStyles(item)
  send 'scheduler.pass' if a pass ran, also after a failed one

  if dateChanged:
    send 'scheduler.date'
  if minuteChanged:
    send 'scheduler.minute'
```

What marks, and what runs the full loop:

- A change the passes read (domain changes except subject,
  description, expansion, fees and priority): its sources; an added
  object with everything under it; a style changed outside a pass, or
  a category's style priority, also what reads it. A name marks only
  what shows it as a style source (a category's items, a parent's
  children), so typing a leaf's name runs nothing.
- A task's planned start, actual start, due or reminder changed, or
  tasks added: their entries; tasks removed: theirs removed.
- A file read or merged: the list rebuilt and the full loop at once,
  so the views first draw the file styled; within a read
  (`taskfile.settle`), quietly
  ([PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#order-and-quiet)). The due soon hours, the
  clock set back: the list rebuilt and the full loop. The appearance
  settings, the theme and the system colours: the full loop.

`TASKCOACH_SCHEDULER_CHECK=1` runs the full loop after every tick's
pass and logs each change it still makes (`[SCHEDULER] missed at
...`). Once a minute, if passes ran, a `[SCHEDULER]` line gives the
ticks, the passes (how many full), their cost (with the viewers'
refresh after each), the objects processed and the timer entries:
fewer than 60 ticks means the UI thread was held.

Each object, and each of the events, runs
isolated (`_run_isolated`): these steps notify listeners (viewers,
reminder dialogs), and one failing listener must not skip the rest of
the pass or keep the date and minute events from being sent. The
Publisher runs each of their subscribers isolated. A failure is logged with the
`[SCHEDULER]` prefix, with its traceback the first time and then a
count every 100 repeats.

> **Key Principle:** MasterScheduler handles TIME-based changes (status updates, reminders, styles). Auto-completion cascades are EVENT-driven via `_on_completion_date_time_changed` to respect user intent when manually unchecking tasks.

---

## Optimizations

**Reference:** `scheduler.py:GlobalTimer._on_tick()`, `MasterScheduler._on_second()`

1. **Single Timestamp Per Tick**: `DateTime.now()` called once, passed to all subscribers
2. **Tuple Comparison**: MasterScheduler stores date/minute as tuples for fast integer comparison
3. **The list's first entry**: the check each second reads one value; a pass runs only for due entries and marked objects
4. **Timestamp Reuse**: Subscribers receive timestamp parameter, no extra `now()` calls

---

## Performance Considerations

Measured on 2026-09-27 with 2000 tasks and dates spread 20 days
around now: the old loop cost 258 ms every second; the master timer
list ran one pass a minute (213 ms) and 59 of 60 ticks did nothing.
With the incremental pass (2026-09-30), dates 60 minutes around now:
about 20 passes a minute, 9 to 19 ms each, instead of 29 of 379 ms
([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#cost-after)).
Profile before optimizing further.

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
3. **Simple lifecycle**: Timer starts on app start and is freed after
   the event loop ends; a tick after the main window is gone is
   skipped ([DEFERRED_CALLS.md](DEFERRED_CALLS.md#end-of-life))
4. **Predictable**: Just check conditions, no complex event chains
5. **Debuggable**: the check mode and the minute trace (above)
6. **Efficient**: Single timestamp, tuple comparisons, pub/sub dispatch

---

## The Master Timer List

The full scan every second was replaced by the master timer list in
2026-09: [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md),
with the costs before and after.
