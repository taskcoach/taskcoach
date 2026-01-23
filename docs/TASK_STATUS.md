# Task Status System

## Overview

Task status is a dynamically computed property of each task, derived from the task's date fields and the current time. It determines the task's visual appearance (color, icon, font) and is used for filtering, status bar counts, system tray tooltips, and HTML export styling.

**See also:**
- `docs/SCHEDULERS.md` — GlobalTimer architecture (the single main loop that drives status updates)
- `docs/legacy/task_states.dot` / `docs/legacy/task_states.png` — Original 2012 state transition diagram (approximate, missing prerequisites and reverse transitions)

---

## Status Values

### Encoding

Each status is a `TaskStatus` singleton object (`domain/task/status.py`) with these attributes:

| `statusString` | Display Text | Icon | FG Color | Condition |
|---|---|---|---|---|
| `"inactive"` | `"Inactive"` | `led_grey_icon` | Grey (192,192,192) | No actual start, planned start in future (or has incomplete prerequisites) |
| `"late"` | `"Late"` | `led_purple_icon` | Purple (160,32,240) | Planned start date has passed, no actual start |
| `"active"` | `"Active"` | `led_blue_icon` | Black (0,0,0) | Actual start date has passed |
| `"duesoon"` | `"Due soon"` | `led_orange_icon` | Orange (255,128,0) | Due date within `dueSoonHours` (default: 24h) |
| `"overdue"` | `"Overdue"` | `led_red_icon` | Red (255,0,0) | Due date has passed |
| `"completed"` | `"Completed"` | `checkmark_green_icon` | Green (0,255,0) | Completion date is set |

Settings key for each status: `"%stasks" % statusString` (e.g., `"activetasks"`)
Configurable in settings sections: `fgcolor`, `bgcolor`, `icon`, `font`

### Identity and Comparison

TaskStatus objects use `statusString` for equality and hashing:
- `__eq__`: compares `self.statusString == other.statusString`
- `__hash__`: `hash(self.statusString)`
- This enables O(1) set membership checks in filtering

---

## State Transitions

```
Inactive ──→ Late ──→ Active ──→ Due soon ──→ Overdue ──→ Completed
    │                    │            │            │
    └────────────────────┴────────────┴────────────┴──→ Completed
```

Transitions are time-driven (status changes as `now` passes date thresholds) or user-driven (setting completion date). The precedence in calculation is:

1. Completed (has completion date)
2. Inactive (has incomplete prerequisites — overrides all date checks)
3. Overdue (due date < now)
4. Due soon (0 <= time left < dueSoonHours)
5. Active (actual start <= now)
6. Late (planned start < now)
7. Inactive (default)

---

## Architecture

### Stored Fields

**File:** `taskcoachlib/domain/task/task.py`

Each task stores three computed status fields:
- `__status_text` — Display text (e.g., `"Active"`, `"Overdue"`)
- `__status_icon` — Icon name (e.g., `"led_blue_icon"`)
- `__status` — Cached TaskStatus object (used internally by `status()`)

Accessor methods:
- `task.statusText()` — Returns display text
- `task.statusIconName()` — Returns icon name
- `task.status()` — Returns TaskStatus object (cached)

### computeStatus() — Single Update Function

Independent calculation that does NOT touch the legacy `__status` cache.
Has its own duplicated status logic, populates the new stored fields.

```python
def computeStatus(self):
    # Independent calculation from task dates (duplicated logic)
    if completionDateTime set: newStatus = completed
    elif prerequisites incomplete: newStatus = inactive
    elif dueDateTime < now: newStatus = overdue
    elif due soon: newStatus = duesoon
    elif actualStart <= now: newStatus = active
    elif plannedStart < now: newStatus = late
    else: newStatus = inactive

    # Update stored fields
    self.__computed_status = newStatus
    self.__status_text = ...      # Derive display text
    self.__status_icon = ...      # Derive icon name from settings

    # Fire event only on actual change
    if oldStatus and newStatus != oldStatus:
        pub.sendMessage('pubsub.task.status', ...)
```

Called from:
- `Task.__init__()` — Initial population on task creation/load
- `recomputeAppearance()` — Immediate update on date changes (called by all date setters)
- `StatusChecker._onSecond()` — Periodic safety net, called on ALL tasks every second

### Event: statusChangedEventType

`task.Task.statusChangedEventType()` returns `"pubsub.task.status"`

Fired by `computeStatus()` only when status actually changes.
Subscribers: status columns in TaskViewer (via column event infrastructure).

### Update Triggers

Status is recomputed in three scenarios:

1. **On load** — `Task.__init__()` calls `computeStatus()` once
2. **On date change** — Date setters (e.g., `setDueDateTime()`) call `recomputeAppearance()` which calls `computeStatus()` at its start. This provides immediate status updates.
3. **Every second** — `StatusChecker._onSecond()` calls `computeStatus()` for all tasks as a periodic safety net for time-based transitions (e.g., task becomes overdue at midnight).

### Timer-Driven Updates (StatusChecker)

**File:** `taskcoachlib/gui/timer.py`
**Instantiated in:** `taskcoachlib/gui/mainwindow.py:_create_window_components()`

The `StatusChecker` subscribes to `timer.second` (the GlobalTimer's 1-second tick) and polls all tasks for time-based transitions:

```
GlobalTimer._onTick() (every 1 second)
    └── pub.sendMessage('timer.second', timestamp=now)
        └── StatusChecker._onSecond(timestamp)
            ├── Transition detection (set-based, fires once per transition):
            │   ├── For each non-completed task: check if dates crossed thresholds
            │   └── Call task.recomputeAppearance() for newly transitioned tasks
            │       ├── Calls computeStatus() → updates status + fires event
            │       └── Updates foreground/background colors based on new status
            │
            └── Safety net:
                └── For ALL tasks: call task.computeStatus()
                    ├── Independent status calculation from dates
                    ├── Updates __computed_status, __status_text, __status_icon
                    └── Fires statusChangedEventType if changed
```

### Immediate Updates (Date Setters)

When a user changes a date field, the update is immediate:

```
setDueDateTime(newDate) / setPlannedStartDateTime(newDate) / etc.
    └── self.recomputeAppearance()
        ├── self.computeStatus()
        │   ├── Recalculates status from current dates
        │   └── Fires 'pubsub.task.status' if status changed
        ├── __computeRecursiveForegroundColor()  (uses status for color)
        └── __computeRecursiveBackgroundColor()
```

### Viewer Columns

Three columns in TaskViewer under the Dates submenu:
- `"status"` — "Status" — Text only (e.g., "Active")
- `"statusIcon"` — "Status icon" — Icon only (LED/checkmark)
- `"statusIconText"` — "Status combo" — Icon + text combined

All subscribe to `statusChangedEventType` for refresh.

---

## Usage Locations

### Sources of Truth

| Location | File:Line | Source of Truth | What It Does |
|----------|-----------|-----------------|--------------|
| Core calculation | `domain/task/task.py:644-673` | Dates + now + dueSoonHours | Computes and caches status |
| StatusChecker | `gui/timer.py:244-287` | **Duplicates date logic** | Detects transitions by comparing dates to now |
| Editor live preview | `gui/dialog/editor.py:708-758` | **Duplicates date logic** | Computes status from form field values |

### Consumers (read task.status() cache)

| Consumer | File:Line | Purpose |
|----------|-----------|---------|
| Status helper methods | `domain/task/task.py:599-631` | `completed()`, `overdue()`, `active()`, etc. |
| Color cascade | `domain/task/task.py:953-968` | Foreground color fallback (own > category > status) |
| Background cascade | `domain/task/task.py:1004-1027` | Background color fallback |
| Font cascade | `domain/task/task.py:1043-1052` | Font fallback |
| Icon cascade | `domain/task/task.py:1072-1121` | Icon fallback |
| ViewFilter | `domain/task/filter.py:151-153` | Hide tasks by status |
| Status bar | `gui/viewer/task.py:89-92` | Task count per status |
| Task list counts | `domain/task/tasklist.py:29-36` | `nrOfTasksPerStatus()` |
| Taskbar tooltip | `gui/taskbaricon.py:242-262` | System tray overdue/duesoon counts |
| Editor display | `gui/dialog/editor.py:620-643` | Shows icon + colored text in Dates tab |
| HTML export | `persistence/html/generator.py:158,285` | CSS class per status |

### Filtering

| Setting | File | Effect |
|---------|------|--------|
| `hideinactivetasks` | `domain/task/filter.py` | Hides tasks where `status() == inactive` |
| `hidelatetasks` | `domain/task/filter.py` | Hides tasks where `status() == late` |
| `hideactivetasks` | `domain/task/filter.py` | Hides tasks where `status() == active` |
| `hideduesoontasks` | `domain/task/filter.py` | Hides tasks where `status() == duesoon` |
| `hideoverduetasks` | `domain/task/filter.py` | Hides tasks where `status() == overdue` |
| `hidecompletedtasks` | `domain/task/filter.py` | Hides tasks where `status() == completed` |

These are per-viewer settings (taskviewer, taskstatsviewer, taskinterdepsviewer, squaretaskviewer, timelineviewer, calendarviewer, hierarchicalcalendarviewer).

### Event Types That Affect Status

The status has no dedicated event type. Changes propagate via:

| Event | When Fired | Effect on Status |
|-------|-----------|-----------------|
| `plannedStartDateTimeChangedEventType` | User changes planned start | May change inactive↔late |
| `actualStartDateTimeChangedEventType` | User changes actual start | May change inactive/late↔active |
| `dueDateTimeChangedEventType` | User changes due date | May change active↔duesoon↔overdue |
| `completionDateTimeChangedEventType` | User changes completion | May change any↔completed |
| `appearanceChangedEventType` | `recomputeAppearance()` called | Signals visual update needed |
| `prerequisitesChangedEventType` | Prerequisites change | May force inactive |

---

## Architectural Issues (Legacy)

### 1. Duplicated Calculation Logic

The status calculation exists in **four places** (including the new `computeStatus()`):

1. **`task.status()`** — legacy cached calculation
2. **`task.computeStatus()`** — new single-source-of-truth (intentional duplication during migration)
3. **`StatusChecker._checkStatusTransitions()`** — reimplements date comparisons to detect transitions
4. **`DatesPage._computeLocalStatus()`** — reimplements for live editor preview using form values

After migration, #1, #3, and #4 will be removed, leaving `computeStatus()` as the sole calculation site.

### 2. No Dedicated Status Event — RESOLVED

`statusChangedEventType` (`"pubsub.task.status"`) now exists, fired by `computeStatus()` only on actual transitions. The new status columns subscribe to it.
Legacy consumers still use `appearanceChangedEventType()` as a proxy.

### 3. StatusChecker Duplicates Logic

The legacy `StatusChecker._checkStatusTransitions()` still does its own date comparisons.
To be removed after migration — `computeStatus()` handles change detection directly.

### 4. Cache Invalidation is Implicit

The legacy cache is still cleared by `recomputeAppearance()` from ~15 call sites.
To be removed after migration — stored fields eliminate the need for cache/invalidation.

---

## Refactor: Single Source of Truth

### Why the Legacy Cache Existed

The legacy `__status` cache was a performance optimization. `status()` is called many
times per task within a single event cycle:
- `statusFgColor()` → `status()`
- `statusBgColor()` → `status()`
- `statusFont()` → `status()`
- `statusIcon()` → `status()`
- `completed()`, `overdue()`, `active()`, etc. → `status()`
- ViewFilter → `status()`

Without caching, each call would redo date comparisons and iterate prerequisites.
The cache made this O(1) after the first call, but required manual invalidation
(`__status = None`) scattered across ~15 call sites via `recomputeAppearance()`.

### Why the New Approach Eliminates the Cache

With `computeStatus()` as the sole writer:
1. **No cache needed** — `statusText()` and `statusIconName()` are simple field reads
2. **No invalidation needed** — the scheduler updates fields every second
3. **No redundant recalculation** — doesn't matter how many consumers read the fields
4. **Built-in change detection** — `statusChangedEventType` fires only on transitions
5. **Single calculation site** — logic lives in one function, not duplicated in 3 places

The old pattern combined calculator + accessor in one method (`status()`), requiring
every consumer to potentially trigger computation. The new pattern separates writer
(scheduler) from readers (columns, filter, editor, etc.).

### Migration Path

1. **Current state:** `computeStatus()` runs in parallel alongside legacy code.
   New columns read `statusText()` / `statusIconName()`. Legacy consumers still
   use `status()` / `statusFgColor()` / etc.

2. **After verification:** Migrate legacy consumers one by one to read from
   `__computed_status` instead of calling `status()`:
   - `statusFgColor()` → use `self.__computed_status` instead of `self.status()`
   - `completed()` → use `self.__computed_status == status.completed`
   - ViewFilter → use stored status instead of calling `task.status()`
   - Editor display → use `task.statusText()` / `task.statusIconName()`

3. **Final cleanup:** Remove legacy `status()` cache, `__status` field, and the
   scattered `__status = None` invalidations. Remove duplicated logic from
   `StatusChecker._checkStatusTransitions()` and `DatesPage._computeLocalStatus()`.

### Staleness Tradeoff — RESOLVED

Immediate updates are now implemented: `recomputeAppearance()` (called by all date
setters) invokes `computeStatus()` at its start. This means:
- User-driven date changes → instant status update (no 1-second delay)
- Time-based transitions → detected within 1 second by StatusChecker
- The only remaining "stale" window is for time-based transitions (up to 1 second),
  which is imperceptible to users.

---

## Configuration

### Settings Keys

For each status `X` (inactive, late, active, duesoon, overdue, completed):

| Section | Key | Default | Purpose |
|---------|-----|---------|---------|
| `fgcolor` | `Xtasks` | See table above | Text color |
| `bgcolor` | `Xtasks` | White | Background color |
| `icon` | `Xtasks` | See table above | Status icon |
| `font` | `Xtasks` | (empty) | Font override |
| `behavior` | `duesoonhours` | 24 | Hours threshold for "due soon" |

### Per-Viewer Filter Settings

Each viewer that shows tasks has `hideXtasks` boolean settings (all default to `False`).

---

## File Reference

| File | Purpose |
|------|---------|
| `taskcoachlib/domain/task/status.py` | TaskStatus class and 6 singleton instances |
| `taskcoachlib/domain/task/task.py` | `status()`, color/icon/font methods, `recomputeAppearance()` |
| `taskcoachlib/domain/task/filter.py` | ViewFilter with status-based hiding |
| `taskcoachlib/domain/task/tasklist.py` | `nrOfTasksPerStatus()` count method |
| `taskcoachlib/gui/timer.py` | GlobalTimer + StatusChecker |
| `taskcoachlib/gui/dialog/editor.py` | Status display in Edit Task Dates tab |
| `taskcoachlib/gui/viewer/task.py` | Status bar counts, filter UI commands |
| `taskcoachlib/gui/taskbaricon.py` | System tray status counts |
| `taskcoachlib/config/defaults.py` | Default colors, icons, fonts, dueSoonHours |
| `persistence/html/generator.py` | HTML export status CSS |
| `docs/legacy/task_states.dot` | Original 2012 state transition diagram (approximate) |
| `docs/SCHEDULERS.md` | GlobalTimer architecture (drives status updates) |
