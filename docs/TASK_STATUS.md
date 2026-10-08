# Task Status System

## Index

1. [Overview](#overview)
2. [Status Values](#status-values)
   - [Encoding](#encoding)
   - [Identity and Comparison](#identity-and-comparison)
3. [State Transitions](#state-transitions)
4. [Architecture](#architecture)
   - [Stored Fields](#stored-fields)
   - [compute_status(): Single Source of Truth](#compute_status-single-source-of-truth-class-method)
   - [compute_stored_status(): Instance Update Method](#compute_stored_status-instance-update-method)
   - [Event: statusChangedEventType](#event-statuschangedeventtype)
   - [Update Triggers](#update-triggers)
   - [Timer-Driven Updates (ComputeStyles)](#timer-driven-updates-computestyles)
   - [Immediate Updates (Date Setters)](#immediate-updates-date-setters)
   - [Viewer Columns](#viewer-columns)
5. [Usage Locations](#usage-locations)
   - [Sources of Truth](#sources-of-truth)
   - [Consumers](#consumers-read-computedstatus)
   - [Filtering](#filtering)
   - [Event Types That Affect Status](#event-types-that-affect-status)
6. [Architectural Issues (Legacy)](#architectural-issues-legacy)
7. [Refactor: Single Source of Truth](#refactor-single-source-of-truth)
   - [Why the Legacy Cache Existed](#why-the-legacy-cache-existed)
   - [Why the New Approach Eliminates the Cache](#why-the-new-approach-eliminates-the-cache)
   - [Migration Path](#migration-path)
   - [Staleness Tradeoff — RESOLVED](#staleness-tradeoff--resolved)
8. [Configuration](#configuration)
   - [Settings Keys](#settings-keys)
   - [Per-Viewer Filter Settings](#per-viewer-filter-settings)
9. [Task Icon Decision Sequence](#task-icon-decision-sequence)
   - [Priority Order](#priority-order)
   - [Computed vs Final Icon](#computed-vs-final-icon)
10. [Appearance Inheritance](#appearance-inheritance)
    - [Appearance Tab Layout (3-Column Grid)](#appearance-tab-layout-3-column-grid)
    - [Task Appearance](#task-appearance)
    - [Category Appearance](#category-appearance)
    - [Style Accessors](#style-accessors)
    - [Notes, Efforts, and Attachments](#notes-efforts-and-attachments)
11. [File Reference](#file-reference)
12. [SSOT Principle: Action vs Display](#ssot-principle-action-vs-display)

---

## SSOT Principle: Action vs Display

**Critical distinction between status for ACTION vs status for DISPLAY:**

| Purpose | Method | When to Use |
|---------|--------|-------------|
| **Action logic** | Direct field check | Cascades, event handlers, business logic |
| **Display/reporting** | `computedStatus()` | UI columns, filtering, status bar |

### Why This Matters

`computedStatus()` is stored, for display: a change of a field it reads updates it at once ([Immediate Updates](#immediate-updates-date-setters)), the clock alone at the loop's timer seconds ([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#master-design)). Action logic reads the fields, which never lag.

```python
# BAD - uses stale cache during event handler:
def completed(self):
    return self.computedStatus() == status.completed

# GOOD - direct SSOT check, always accurate:
def completed(self):
    return self.completionDateTime() != self.maxDateTime
```

### Example: Cascade Bug

The bug behind the rule, from before the immediate updates: when a child task was completed, `_on_completion_date_time_changed` fires. At that moment:
- Child's `completionDateTime` is set (accurate)
- Child's `computedStatus()` is stale (not yet recomputed)
- Parent calls `allChildrenCompleted()` → `child.completed()` → returns False!

**Fix:** `completed()` must use direct datetime check, not `computedStatus()`.

### Rule

Action methods (`completed()`, `allChildrenCompleted()`, etc.) must use **direct field checks**. The computed status system is for display/reporting only.

---

## Appearance Inheritance Overview

Own, derived and effective values are separate fields; for other task
fields the same split is postponed
([TASK_FIELDS.md](TASK_FIELDS.md#postponed-base-and-effective-fields)).

### ComputeStyles in the Master Loop

The appearance SSOT system is computed by the master loop (`ComputeStyles`), which runs at the
seconds that matter ([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#master-design)): the seconds time changes a status, and the second after a change it reads. This provides:

1. **Eventual consistency** - A change shows at the next tick (within a second)
2. **Simplified architecture** - One loop, not a trigger per field and follower
3. **Catches time-based changes** - Each status's next change is a second in the timer list

**Processing order:** Categories → Tasks → Notes → Attachments

**Key classes:**
- `MasterScheduler` in `scheduler.py` - At each due second or after a change, processes the objects concerned and what reads them, each once (`compute_styles()`; for tasks the status and reminder too)
- `compute_derived(obj, field_type)` - Computes derived value from sources
- `compute_effective(obj, field_type)` - Computes effective from override + derived

**Category stylePriority:**
Tasks with multiple categories use `stylePriority` to determine which category's style wins.
Higher priority wins. Default is 0.

### Object Type Summary

| Object Type | Derived From | SSOT Methods | Appearance Tab |
|-------------|--------------|--------------|----------------|
| **Task** | Categories → Parent task → Status | `effectiveXxx()` | Yes |
| **Category** | Parent category → System Theme | `effectiveXxx()` | Yes |
| **Note** | Categories → Parent note → System Theme | `effectiveXxx()` | Yes |
| **Attachment** | System Theme only (no inheritance) | `effectiveXxx()` | Yes |
| **Effort** | Task (always) | None | **No** - uses task's appearance |

**Key points:**
- All object types with appearance tabs have SSOT `effectiveXxx()` and `derivedXxx()` methods
- Complexity varies: Tasks have most sources, Attachments have fewest (just override or system theme)
- Notes inherit from their categories, then their parent note (never from their owner)
- Efforts have no appearance tab; they always display using their task's appearance

**"Nothing Set" Convention:**
- Colors/Fonts: `None` = nothing set (default in `object.py`)
- Icons: `""` (empty string) = nothing set (default in `object.py`)
- Both are **falsy** in Python, so `if value:` works for both

**System Theme Constants:**
- `base.SYSTEM_FG_COLOR` = "SYS_COLOUR_WINDOWTEXT"
- `base.SYSTEM_BG_COLOR` = "SYS_COLOUR_WINDOW"
- `base.SYSTEM_FONT` = "SYS_DEFAULT_GUI_FONT"
- `base.SYSTEM_THEME_SOURCE` = "System Theme"
- **Icons:** `""` when nothing is set; notes and attachments then show their type's icon (`TYPE_DEFAULT_ICONS`, source "System Theme"), a category shows "N/A"

**SSOT Method Contract:**

**Effective accessors** use separate methods:

| Call | Returns | Purpose |
|------|---------|---------|
| `effectiveXxx()` | value | Actual value (None/"" if nothing set) |
| `effectiveXxxDefault()` | default | System theme constant to use when value is empty |
| `effectiveXxxSource()` | source | "[Override]", "[Category] Name", "[Tracking]", etc. |

**Derived accessors** use separate methods:

| Call | Returns | Purpose |
|------|---------|---------|
| `derivedXxx()` | value | The computed value (None/"" if nothing set) |
| `derivedXxxSource()` | source | "[Category] Name", "[Status]", etc. |

All accessors are simple getters that read from Attribute fields in the base `Object` class.

```python
# All accessors are simple getters from Attribute fields in base Object class

# EFFECTIVE accessors (in object.py)
def effectiveFgColor(self):
    """Return effective foreground color value."""
    return self.__effectiveFgColorValue.get()

def effectiveFgColorDefault(self):
    """Return effective foreground color default (system theme constant)."""
    return self.__effectiveFgColorDefault.get()

def effectiveFgColorSource(self):
    """Return effective foreground color source ("[Override]", "[Category] Name", etc)."""
    return self.__effectiveFgColorSource.get()

# DERIVED accessors (in object.py)
def derivedFgColor(self):
    """Return derived foreground color value."""
    return self.__derivedFgColorValue.get()

def derivedFgColorSource(self):
    """Return derived foreground color source."""
    return self.__derivedFgColorSource.get()
```

- **All accessors** are simple Attribute getters in `object.py`
- **compute_derived()** in `appearance.py` computes and writes to SSOT
- **compute_effective()** in `appearance.py` computes effective from derived + override
- UI resolves: `color = resolve_color(actual if actual else default)`

**Plural icons:** removed 2026-09-29, **ruled by designer**
([ICON_LIBRARY.md](ICON_LIBRARY.md#removed-plural-icons), why): every
view shows the effective icon as is; a task with subtasks shows its
status icon like any task.

---

## Overview

Task status is a dynamically computed property of each task, derived from the task's date fields and the current time. It determines the task's visual appearance (color, icon, font) and is used for filtering, status bar counts, system tray tooltips, and HTML export styling.

**See also:**
- `docs/SCHEDULERS.md` — GlobalTimer architecture (the single main loop that drives status updates)
- `docs/ICON_LIBRARY.md` — Icon sources, structure, and adding new icons
- `docs/legacy/task_states.dot` / `docs/legacy/task_states.png` — Original 2012 state transition diagram (approximate, missing prerequisites and reverse transitions)

---

## Status Values

### Encoding

Each status is a `TaskStatus` singleton object (`domain/task/status.py`) with these attributes:

| `status_string` | Display Text | Icon | FG Color | Condition |
|---|---|---|---|---|
| `"inactive"` | `"Inactive"` | `taskcoach_actions_led_grey_icon` | Grey (192,192,192) | No actual start, planned start in future (or has incomplete prerequisites) |
| `"late"` | `"Late"` | `nuvola_actions_ledpurple` | Purple (160,32,240) | Planned start date has passed, no actual start |
| `"active"` | `"Active"` | `nuvola_actions_ledblue` | Black (0,0,0) | Actual start date has passed |
| `"duesoon"` | `"Due soon"` | `nuvola_actions_ledorange` | Orange (255,128,0) | Due date within `dueSoonHours` (default: 24h) |
| `"overdue"` | `"Overdue"` | `nuvola_actions_ledred` | Red (255,0,0) | Due date has passed |
| `"completed"` | `"Completed"` | `checkmark_green_icon` | Green (0,255,0) | Completion date is set |

Settings key for each status: `"%stasks" % status_string` (e.g., `"activetasks"`)
Configurable in settings sections: `fgcolor`, `bgcolor`, `icon`, `font`

### Identity and Comparison

TaskStatus objects use `status_string` for equality and hashing:
- `__eq__`: compares `self.status_string == other.status_string`
- `__hash__`: `hash(self.status_string)`
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

Each task stores four computed status fields:
- `__computed_status`: the TaskStatus object
- `__status_text`: display text (e.g., `"Active"`, `"Overdue"`)
- `__status_icon_id`: icon name (e.g., `"nuvola_actions_ledblue"`)
- `__status_source`: why the task has this status

Accessor methods:
- `task.computedStatus()` — Returns TaskStatus object (single source of truth) ✓
- `task.statusText()` — Returns display text ✓
- `task.status_icon_id()` — Returns icon ID ✓

### compute_status(): Single Source of Truth (Class Method)

**File:** `taskcoachlib/domain/task/task.py`

The `Task.compute_status()` class method is the **single source of truth** for status calculation.
It takes date values as parameters and returns `(TaskStatus, source_string)` tuple.

```python
@classmethod
def compute_status(cls, completion_dt, due_dt, actual_start_dt,
                   planned_start_dt, due_soon_hours,
                   has_incomplete_prerequisites, now=None,
                   max_date_time=None):
    """Compute task status from date values. SINGLE SOURCE OF TRUTH."""
    # Priority order: completed > inactive(prereqs) > overdue > duesoon > active > late > inactive
    if completion_dt != max_date_time:
        return status.completed, _("Completion date is set")
    if has_incomplete_prerequisites:
        return status.inactive, _("Has incomplete prerequisites")
    if due_dt != max_date_time and due_dt < now:
        return status.overdue, _("Due date has passed")
    # ... etc
    return status.inactive, _("No actual start date")
```

### compute_stored_status(): Instance Update Method

The `task.compute_stored_status()` instance method calls `compute_status()` with the task's
actual values and stores the results in the task's fields.

Called from:
- `Task.__init__()` — Initial population on task creation/load
- `_update_status()`: at once after a change of what it reads (dates,
  completion, prerequisites, subtasks added or removed)
- `MasterScheduler._compute_task()`: when the loop processes the task, at
  that second, before `compute_styles()`

### Event: statusChangedEventType

`task.Task.statusChangedEventType()` returns `"task.status"` (a
Publisher event, the task as source)

Fired by `compute_stored_status()` only when the status changes.
Subscribers: status columns in TaskViewer (via column event infrastructure).

### Update Triggers

Status is recomputed in three scenarios:

1. **On load:** `Task.__init__()` calls `compute_stored_status()` once.
2. **On a change of what it reads:** the date setters (e.g.
   `set_due_date_time()`), completion, prerequisites and subtasks added or
   removed call `_update_status()`, which calls `compute_stored_status()`,
   so the status updates at once; the styles follow at the loop's next
   pass.
3. **When the loop processes the task** (a timer second of it lands, a
   change marks it, or a full loop runs): `MasterScheduler._compute_task()`
   calls `compute_stored_status()` at that second, then `compute_styles()`.

### Timer-Driven Updates (ComputeStyles)

**File:** `taskcoachlib/gui/scheduler.py`
**Instantiated in:** `taskcoachlib/gui/mainwindow.py:_create_window_components()`

`MasterScheduler` subscribes to `timer.second` (the GlobalTimer's 1-second tick) and,
when its timer list holds a due entry or an object is marked, processes those
objects and what reads them (the full loop when every object is concerned). For
each task, the per-object flow is:

```
GlobalTimer._on_tick() (every 1 second)
    └── patterns.Event('timer.second', self, now).send()
        └── MasterScheduler._on_second(event)
            └── A due second? For each task:
                1. task.compute_stored_status()
                │   ├── Calls Task.compute_status() with task's dates
                │   ├── Updates __computed_status, __status_text, __status_icon_id
                │   └── Fires statusChangedEventType if changed
                2. compute_styles(task)
                    ├── compute_derived(task, field_type) for each field
                    └── compute_effective(task, field_type) for each field
```

See docs/SCHEDULERS.md for the complete MasterScheduler processing flow.

### Immediate Updates (Date Setters)

When a user changes a date field, the status updates at once; the
colours, font and icon follow at the master loop's next pass (within a
second):

```
set_due_date_time(newDate) / set_planned_start_date_time(newDate) / etc.
    └── self._update_status()
        └── self.compute_stored_status()
            ├── Recalculates status from current dates
            └── Fires 'task.status' if status changed
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

| Location | File | Source of Truth | What It Does |
|----------|------|-----------------|--------------|
| Core calculation | `domain/task/task.py` | Dates + now + dueSoonHours | Computes and caches status |
| Master loop | `gui/scheduler.py` | `_compute_task()` | Stores the status at the tick's second, then `compute_styles()` computes the derived and effective appearance |

### Consumers (read computedStatus())

| Consumer | File | Purpose |
|----------|------|---------|
| Status helper methods | `domain/task/task.py` | `overdue()`, `active()`, etc.; `completed()` reads the completion date ([Rule](#rule)) |
| Status styles | `domain/task/task.py` | `statusFgColor()`, `statusBgColor()`, `statusFont()`, `status_icon_id()`, read by `compute_derived()` |
| ViewFilter | `domain/task/filter.py` | Hide tasks by status |
| Status bar | `gui/viewer/task.py` | Task count per status |
| Task list counts | `domain/task/tasklist.py` | `nr_of_tasks_per_status()` |
| Taskbar tooltip | `gui/taskbaricon.py` | System tray overdue/duesoon counts |
| Editor display | `gui/dialog/editor.py` | Shows icon + colored text in Dates tab |
| HTML export | `persistence/html/generator.py` | CSS class per status |

### Filtering

| Setting | File | Effect |
|---------|------|--------|
| `hideinactivetasks` | `domain/task/filter.py` | Hides tasks where `computedStatus() == inactive` |
| `hidelatetasks` | `domain/task/filter.py` | Hides tasks where `computedStatus() == late` |
| `hideactivetasks` | `domain/task/filter.py` | Hides tasks where `computedStatus() == active` |
| `hideduesoontasks` | `domain/task/filter.py` | Hides tasks where `computedStatus() == duesoon` |
| `hideoverduetasks` | `domain/task/filter.py` | Hides tasks where `computedStatus() == overdue` |
| `hidecompletedtasks` | `domain/task/filter.py` | Hides tasks where `computedStatus() == completed` |

These are per-viewer settings (taskviewer, taskstatsviewer, squaretaskviewer, timelineviewer, calendarviewer, hierarchicalcalendarviewer).

### Event Types That Affect Status

These changes can change the status, which then sends `task.status`:

| Event | When Fired | Effect on Status |
|-------|-----------|-----------------|
| `plannedStartDateTimeChangedEventType` | User changes planned start | May change inactive↔late |
| `actualStartDateTimeChangedEventType` | User changes actual start | May change inactive/late↔active |
| `dueDateTimeChangedEventType` | User changes due date | May change active↔duesoon↔overdue |
| `completionDateTimeChangedEventType` | User changes completion | May change any↔completed |
| `prerequisitesChangedEventType` | Prerequisites change | May force inactive |

---

## Architectural Issues (Legacy)

### 1. Duplicated Calculation Logic — RESOLVED

**Status:** Complete. Single source of truth implemented.

The status calculation now exists in **one place only**:

- **`Task.compute_status()`**: class method, single source of truth

All other code calls this method:
- **`task.compute_stored_status()`**: instance method that calls `compute_status()` and stores results
- **`MasterScheduler._compute_task()`**: calls `task.compute_stored_status()` for each task the loop processes

The `compute_status()` method returns `(TaskStatus, source_string)` tuple, providing both the status and an explanation of why the task has that status.

### 2. No Dedicated Status Event — RESOLVED

`statusChangedEventType` (`"task.status"`) now exists, fired by `compute_stored_status()` only on actual transitions. The new status columns subscribe to it.
The task filter and the tray, which used the old appearance event as
a proxy, listen to it since the views moved to the effective styles
([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md), To Do
35).

### 3. StatusChecker Duplicates Logic — RESOLVED

StatusChecker has been merged into the scheduler. `MasterScheduler._compute_task()`
calls each task's `compute_stored_status()` immediately before `compute_styles()`. This
eliminates the duplicated date logic and guarantees correct ordering: status is always
fresh when appearance values are computed.

### 4. Cache Invalidation is Implicit: RESOLVED

The legacy style cache and `recomputeAppearance()` are removed with the
views' move to the effective styles
([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md), To Do
35). `_update_status()` keeps only the immediate status.

### 5. Derived/Effective Event Types Used Wrong Prefix — RESOLVED

The derived and effective Attribute fields (on base `Object`, inherited by
all domain types) had event type strings prefixed with `"pubsub."` — e.g.
`"pubsub.derived.fgColor"`, `"pubsub.effective.icon"`. The Attribute
callbacks correctly used `event.addSource()` (legacy Publisher dispatch),
but the `"pubsub."` prefix caused the viewer's `__start_observing()` to
subscribe via `pub.subscribe` (broadcast) instead of `registerObserver`
(sender-filtered). The viewer never received these notifications because
pypubsub and the legacy Publisher are separate dispatch systems.

**Fix:** dropped the `"pubsub."` prefix from all 8 derived + 8 effective
event type strings. The viewer now uses `registerObserver` for these types,
correctly receiving `event.addSource()` notifications via sender-filtered
dispatch. No callback or consumer changes were needed.

See [PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#signal-dispatch) for the
per-instance dispatch requirement and naming convention.

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

With `compute_stored_status()` as the sole writer:
1. **No cache needed** — `statusText()` and `status_icon_id()` are simple field reads
2. **No invalidation needed**: the master loop updates the fields whenever a change or a time condition calls for it
3. **No redundant recalculation** — doesn't matter how many consumers read the fields
4. **Built-in change detection** — `statusChangedEventType` fires only on transitions
5. **Single calculation site** — logic lives in one function, not duplicated in 3 places

The old pattern combined calculator + accessor in one method (`status()`), requiring
every consumer to potentially trigger computation. The new pattern separates writer
(scheduler) from readers (columns, filter, editor, etc.).

### Migration Path

1. **Before:** `compute_status()` ran alongside the legacy code; the
   legacy consumers used `status()`.

2. **Done:** the public accessor `computedStatus()`; the consumers moved
   to it one by one:

   | Consumer | File | Status |
   |----------|------|--------|
   | ViewFilter.filterTask() | filter.py | ✓ Done |
   | completed() | task.py | ✓ Reads the completion date ([Rule](#rule)) |
   | overdue() | task.py | ✓ Done |
   | inactive() | task.py | ✓ Done |
   | active() | task.py | ✓ Done |
   | dueSoon() | task.py | ✓ Done |
   | late() | task.py | ✓ Done |
   | statusFgColor() | task.py | ✓ Done |
   | statusBgColor() | task.py | ✓ Done |
   | statusFont() | task.py | ✓ Done |
   | status_icon_id() | task.py | ✓ Done (now accessor) |
   | nr_of_tasks_per_status() | tasklist.py | ✓ Done |
   | Editor display | editor.py | ✓ Done (uses derivedXxx/effectiveXxx) |
   | Appearance tab 3-col layout | editor.py | ✓ Done |
   | Task derivedXxx(explain) | task.py | ✓ Done |
   | Task effectiveXxx(explain) | task.py | ✓ Done |
   | Category derivedXxx(explain) | category.py | ✓ Done |
   | Category effectiveXxx(explain) | category.py | ✓ Done |
   | compute_status() centralized | task.py | ✓ Done (class method, no duplication) |
   | computedStatus(explain) | task.py | ✓ Done |
   | Dates tab status source | editor.py | ✓ Done (uses computedStatus(explain=True)) |
   | Font picker preview colors | editor.py | ✓ Done (uses effectiveFgColor/effectiveBgColor) |
   | Path tab icons | editor.py | ✓ Done (uses effectiveIcon) |
   | Category cascade on load | category.py | ✓ Done (centralized in _computeEffectiveAppearance) |
   | Note effectiveXxx(explain) | note.py | ✓ Done |
   | Attachment effectiveXxx(explain) | attachment.py | ✓ Done |
   | Tracking icon in derived/effective | appearance.py | ✓ Done (highest-priority derived, skips override) |
   | Plural/singular icon transform | object.py | ✓ Removed (to do 58) |
   | Selected icon variant (open/closed folder) | object.py | ✓ Removed |
   | Every view, widget, export and the tray | gui, widgets, persistence | ✓ Done (`shown_*()`, To Do 35) |

3. **Final cleanup (done 2026-09-28):** the legacy `status()` cache, the
   `__status` field, its invalidations and the loop's
   `recomputeLegacyStatus()` are removed. They differed from
   `computedStatus()` in one rule: the loop's update counted only a
   task's own prerequisites, so a blocked task's subtask looked late
   while its status column and the filters said inactive.

### Staleness Tradeoff — RESOLVED

Immediate updates are implemented: `_update_status()` (called by the
date setters, completion, prerequisites and subtask changes) runs
`compute_stored_status()`. This means:
- User-driven date changes → instant status update (no 1-second delay)
- Time-based transitions → detected within 1 second by the master loop
- The styles follow at the loop's next pass, within a second, which is
  imperceptible to users.

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

## Task Icon Decision Sequence

The task icon every view shows, `shown_icon_id()`, is the effective
icon the master loop computes (`compute_derived()`, `compute_effective()`)
from the following priority sequence. The first match wins; a task
with subtasks shows the same icon (no plural icons since To Do 58).

### Priority Order

```
1. Effort Tracking
   └── If task.isBeingTracked() is True → "nuvola_apps_clock"
   └── Shown when user is actively tracking time on this task

2. Own Icon Override
   └── task.icon_id(): icon set directly on the task
   └── User can set this in the Appearance tab of the task editor

3. Category Icon
   └── The task's categories by stylePriority → category.effectiveIcon()
   └── First category with an icon wins

4. Parent Task Icon
   └── parent.effectiveIcon(), unless it comes from the parent's own
       status or tracking: each task shows its own

5. Status Icon
   └── status_icon_id(), stored by compute_stored_status()
   └── Determined by task status: active, inactive, late, duesoon, overdue, completed
   └── Configured in Preferences > Statuses (light and dark theme)
```

### Computed vs Final Icon

| Term | Definition | Storage |
|------|------------|---------|
| **Status Icon** | Icon based on task status alone, in the current theme | `status_icon_id()`, from `TaskStatus.icon_id(settings)` |
| **Derived Icon** | Tracking, categories, parent or status (before override) | `derivedIcon()` |
| **Effective Icon** | Override, else derived | `effectiveIcon()` |
| **Shown Icon** | The effective icon: what the views draw | `shown_icon_id()` |

---

## Appearance Inheritance

Both Tasks and Categories support appearance inheritance (icon, foreground color, background color, font).
The Appearance tab in the editor shows three sections: **Derived values**, **Override values**, and **Effective values**.

### Appearance Tab Layout (3-Column Grid)

```
APPEARANCE TAB (3-column grid: Label, Control, Source)
═══════════════════════════════════════════════════════════════

Derived values            Source                   ←── title spans 2 cols, Source in col 2
Icon          [bitmap]           [Category] Work
Foreground    [picker]           [Status] Inactive
Background    [picker]           [Task] ParentTask
Font          [picker]           [Category] Work

───────────────────────────────────────────────── ←── spans 3 cols
Override values                                   ←── title spans 2 cols, col 2 empty
Icon          [icon selector─────────────────────] ←── spans 2 cols
Foreground    [checkbox + picker─────────────────] ←── spans 2 cols
Background    [checkbox + picker─────────────────] ←── spans 2 cols
Font          [font picker───────────────────────] ←── spans 2 cols

───────────────────────────────────────────────── ←── spans 3 cols
Effective values          Source                   ←── title spans 2 cols, Source in col 2
Icon          [bitmap]           [Override]
Foreground    [picker]           [Category] Work
Background    [picker]           [Status] Active
Font          [picker]           System Theme
```

**Column spanning:**
- Section headers: title spans columns 0-1, optional "Source" label in column 2
- Separator lines: explicitly span all 3 columns
- Derived/Effective rows: 3 controls (label, control, source) → 1 col each
- Override rows: 2 controls (label, control) → label=1 col, control=2 cols

**Source column** (gray text) shows where each value comes from:
- `[Category] Name`: from a category
- `[Task] Name`: from parent task
- `[Note] Name`: from parent note
- `[Status] StatusName`: from task status (e.g., Inactive, Active, Overdue)
- `[Tracking]`: task is being tracked (effort in progress), icon only
- `[Override]`: user set this value
- `System Theme`: no value set: the system's colours and fonts, the type's icon for notes and attachments
- `N/A`: no icon (a category without one)

### Task Appearance

Tasks **always** have derived values because they always have a status. The inheritance cascade is:

```
Derived values (read-only display):
├── Icon: tracking > category > parent > status
├── Foreground: category > parent > status
├── Background: category > parent > status
└── Font: category > parent > status

Override values (editable):
├── Icon: own icon set directly on task (skipped when tracking)
├── Foreground: own foreground color
├── Background: own background color
└── Font: own font
```

The status always provides a fallback, so derived values are never empty for tasks.
Tracking icon (`clock_icon`) is the highest-priority derived source for icon — it
also skips user overrides in the effective computation.

### Category Appearance

Categories inherit appearance from their **parent category**.

Derived values are computed by `compute_derived()` and stored as SSOT Attribute fields.
Value and source are separate accessors:

```
derivedFgColor()       → value (parent's effective color, or None)
derivedFgColorSource() → source string ("[Category] ParentName" or "System Theme")
derivedIcon()          → value (parent's effective icon, or "")
derivedIconSource()    → source string ("[Category] ParentName" or "N/A")
```

**UI usage:** `color = resolve_color(item.derivedFgColor() or SYSTEM_FG_COLOR)`
Icons have no default - UI displays "N/A" when source is empty.

#### Effective Appearance Fields (Single Source of Truth)

**File:** `taskcoachlib/domain/base/object.py`

All domain objects have SSOT appearance fields as `Attribute` objects defined in base `Object`.
These are written by `compute_derived()` and `compute_effective()` stored procedures, called
by the master loop (`ComputeStyles`).

**Derived accessors** (value and source are separate methods):

| Value Method | Source Method |
|--------------|---------------|
| `derivedFgColor()` | `derivedFgColorSource()` |
| `derivedBgColor()` | `derivedBgColorSource()` |
| `derivedIcon()` | `derivedIconSource()` |
| `derivedFont()` | `derivedFontSource()` |

**Effective accessors** (value, default, and source are separate methods):

| Value Method | Default Method | Source Method |
|--------------|----------------|---------------|
| `effectiveFgColor()` | `effectiveFgColorDefault()` | `effectiveFgColorSource()` |
| `effectiveBgColor()` | `effectiveBgColorDefault()` | `effectiveBgColorSource()` |
| `effectiveIcon()` | — (no default for icons) | `effectiveIconSource()` |
| `effectiveFont()` | `effectiveFontDefault()` | `effectiveFontSource()` |

**UI usage:**
```python
# Effective values - use separate accessor methods
actual = item.effectiveFgColor()
default = item.effectiveFgColorDefault()
source = item.effectiveFgColorSource()
color = resolve_color(actual if actual else default)
source_label.SetLabel(source)

# Derived values - use separate accessor methods
value = item.derivedFgColor()
source = item.derivedFgColorSource()
```

**SSOT Principle — Stored Procedure Pattern:**

**Location:** `taskcoachlib/domain/base/appearance.py`

Two stored procedures handle appearance calculations:

---

#### Stored Procedure: compute_derived

```
compute_derived(object_ref, field_type)

INPUTS:  object_ref (domain object), field_type ('fgColor', 'bgColor', 'font', 'icon')
OUTPUTS: calls object's setDerivedXxx(value, source) Attribute setter
```

**Behavior:**
1. Determine object type (Task, Category, Note, Attachment)
2. For Tasks: check categories → parent task → status (in priority order)
3. For Categories/Notes: check parent's effective value
4. Write via object's Attribute-based setter (fires change event automatically)

**Called by:** the master loop (`ComputeStyles`)

---

#### Stored Procedure: compute_effective

```
compute_effective(object_ref, field_type)

INPUTS:  _derived_{field}_value, _derived_{field}_source, override value
OUTPUTS: _effective_{field}_value, _effective_{field}_default, _effective_{field}_source
```

**Behavior:**
1. Read derived value/source from object's Attribute getters
2. Read override value from object's override getter
3. Compute: `effective = override if override else derived`
4. Write via object's Attribute-based setter (fires change event automatically)

**Called by:** the master loop (`ComputeStyles`)

---

#### Pattern

ComputeStyles polling pattern (eventual consistency):
1. User changes override value (or category assignment, status, etc.)
2. The change pushes the current second; the master loop (`ComputeStyles`) runs at the next tick
3. For each object: `compute_derived()` then `compute_effective()` for each field type
4. Attribute.set() fires change events only when value actually changes
5. UI subscribers (editor Appearance tab) update on per-field change events

---

#### Field Types

`'fgColor'`, `'bgColor'`, `'font'`, `'icon'`

#### SSOT Fields

| Prefix | Fields | Example |
|--------|--------|---------|
| `_derived_` | value, source | `derivedFgColor()`, `derivedFgColorSource()` |
| `_effective_` | value, default (except icon), source | `effectiveFgColor()`, `effectiveFgColorDefault()`, `effectiveFgColorSource()` |

---

#### Update Mechanism: the Master Loop

**No per-field triggers or explicit cascade needed.** The master loop (`ComputeStyles`) runs at each due second, which every change it reads pushes:

```
ComputeStyles (each pass of the master loop)
  └── For each object in taskFile (tasks, categories, notes, attachments):
      └── For each field_type in ('fgColor', 'bgColor', 'font', 'icon'):
          1. compute_derived(object, field_type)
          2. compute_effective(object, field_type)
```

Its pass catches, at the next tick:
- Category assignment/removal
- Parent relationship changes
- Status changes (time-based transitions)
- Override value changes

A file read or merged runs the full loop at once, before the views
draw it.

#### SSOT Readers (for UI)

**Effective values** — use object accessor methods directly:

```python
actual = item.effectiveFgColor()        # value
default = item.effectiveFgColorDefault() # system theme constant
source = item.effectiveFgColorSource()   # source label
```

**Derived values** — use object accessor methods:

```python
value = item.derivedFgColor()        # value
source = item.derivedFgColorSource() # source label
```

UI components should:
1. Read from SSOT via object accessor methods
2. Subscribe to per-field change events (e.g., `derivedFgColorChangedEventType()`, `effectiveFgColorChangedEventType()`)
3. When event fires, re-read from SSOT to update display

---

#### Rules

1. Trigger fires ONLY when INPUT field in SSOT changes
2. Write to OUTPUT fields ONLY if value changed
3. Send an event ONLY if output changed (for UI refresh)

---

#### Volatile Fields

**SSOT fields are volatile** — they are NOT persisted to the task file.
See ATTRIBUTE_PATTERN.md §Volatile vs Persisted Attributes for the general pattern.

The derived and effective Attribute fields are:
- **Not stored**: not written to the file, not in the undo log's
  snapshots
- **Computed by the full loop** as the file is read, before the
  views draw it

**Why volatile?**
- Effective values are computed from persisted data (overrides, parent relationships)
- No need to persist what can be recomputed
- Reduces file size and avoids stale value problems

**No post-load initialization needed**: the full loop the file read
runs populates all volatile fields.

---

#### Data Flow (SSOT Principle)

**Attribute fields defined in object.py** — derived and effective values are Attribute objects
with automatic change event firing via `Attribute.set()`.

**Application startup / file load sequence:**

```
1. App starts, loads data file
   └── Objects created with override values, parent relationships
   └── The full loop at once: all objects get status + derived + effective values
       before the views draw them

2. MasterScheduler ticks (timer.second)

3. Ongoing: the master loop runs at each due second
   └── Any data change (override, category, status, parent) is picked up
   └── Attribute.set() fires per-field change events when values change
   └── UI subscribers update automatically
```

**Key insight:** No per-field triggers needed. A change the loop reads pushes the current
second and the next pass recomputes everything, with eventual consistency (1-2 second
latency).

---

**Data Model Storage:**

Appearance values stored as `Attribute` objects on base `Object` class in `object.py`.
Each Attribute fires a change event when its value is set via `Attribute.set()`
(see ATTRIBUTE_PATTERN.md for the Attribute API).

```
Derived (Attribute fields, written by compute_derived):
  _derived_fgColor       (value)    _derived_fgColor_source
  _derived_bgColor       (value)    _derived_bgColor_source
  _derived_font          (value)    _derived_font_source
  _derived_icon          (value)    _derived_icon_source

Effective (Attribute fields, written by compute_effective):
  _effective_fgColor     (value)    _effective_fgColor_default    _effective_fgColor_source
  _effective_bgColor     (value)    _effective_bgColor_default    _effective_bgColor_source
  _effective_font        (value)    _effective_font_default       _effective_font_source
  _effective_icon        (value)    — (no default for icons)      _effective_icon_source
```

Accessor methods are generated by Attribute fields and return stored values directly.

---

**Change Detection:**

1. The master loop (`ComputeStyles`) runs at each due second
2. Calls `compute_derived()` and `compute_effective()` for all objects
3. `Attribute.set()` compares new vs prior value (see ATTRIBUTE_PATTERN.md)
4. If changed: fires per-field change event (e.g., `derivedFgColorChangedEventType()`)
5. UI subscribers update display

**Self-limiting:** Attribute.set() only fires events when value actually changes.

**Benefits:**
- **Universal:** One loop handles all object types and all change sources
- **No triggers needed:** Catches time-based transitions, category changes, parent changes, etc.
- **Eventual consistency:** 1-2 second latency, acceptable for appearance updates
- **Simple:** No complex trigger/cascade logic to maintain

#### Legacy Code Compatibility: RESOLVED

The legacy `recursive=True` style accessors, their caches and the
colour and font mixing of several categories are removed; every view
draws the effective styles through `shown_fg_color()`,
`shown_bg_color()`, `shown_font()` and `shown_icon_id()`, which turn
system theme values into None for the widgets
([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#views-on-the-effective-styles)).

#### Task Effective Appearance

Tasks have `derivedXxx()` / `derivedXxxSource()` and `effectiveXxx()` / `effectiveXxxSource()` accessor methods.

**Task Appearance Cascade (priority order) — computed by `compute_derived()`:**

```
1. Task's direct categories
   └── Use category.effectiveFgColor() etc.
   └── Source: "[Category] CategoryName"

2. Parent task's effective value (if child task has NO direct categories)
   └── Child task asks parent.effectiveFgColor() etc.
   └── Not when it comes from the parent's own status or tracking
       (source "[Status] ..." or "[Tracking]"): each task shows its own
   └── Source: "[Task] ParentTaskName"

3. Status appearance (fallback - task always has a status)
   └── status_icon_id(), statusFgColor(), statusBgColor(), statusFont()
   └── Source: "[Status] StatusName" (e.g., "[Status] Inactive", "[Status] Active")
```

**`effectiveXxx()` is simple:** tracking (icon only) OR own override OR derivedXxx()
- If tracking effort → Source: "[Tracking]" (skips override)
- If own override set → Source: "[Override]"
- Else → delegates to `derivedXxx()`

**SSOT accessors** (defined as Attribute fields in base `Object`, written by `compute_derived()` and `compute_effective()`):

**Derived** (value and source are separate methods):

| Value Method | Source Method |
|--------------|---------------|
| `derivedFgColor()` | `derivedFgColorSource()` |
| `derivedBgColor()` | `derivedBgColorSource()` |
| `derivedIcon()` | `derivedIconSource()` |
| `derivedFont()` | `derivedFontSource()` |

**Effective** (value, default, and source are separate methods):

| Value Method | Default Method | Source Method |
|--------------|----------------|---------------|
| `effectiveFgColor()` | `effectiveFgColorDefault()` | `effectiveFgColorSource()` |
| `effectiveBgColor()` | `effectiveBgColorDefault()` | `effectiveBgColorSource()` |
| `effectiveIcon()` | — (no default) | `effectiveIconSource()` |
| `effectiveFont()` | `effectiveFontDefault()` | `effectiveFontSource()` |

**Note:** Tasks always have status fallback, so derived values are never empty for Tasks.

**Source label patterns:**
- `"[Override]"` — user set this value directly
- `"[Tracking]"` — task is being tracked (icon only, skips override)
- `"[Category] WorkCategory"` — from a category's effective value
- `"[Task] ParentTaskName"` — from parent task's effective value
- `"[Status] Inactive"` — from task status (includes status name)
- `"System Theme"` — (Categories/Notes/Attachments only, not Tasks)

### Style Accessors

**File:** `taskcoachlib/domain/base/object.py`

| Method | Behavior |
|--------|----------|
| `foregroundColor()`, `backgroundColor()`, `font()`, `icon_id()` | Own value only (the override) |
| `effectiveFgColor()` etc. | The master loop's effective value, "SYS_..." for the system theme |
| `shown_fg_color()`, `shown_bg_color()`, `shown_font()` | Effective value, None for the system theme: what the views draw |
| `shown_icon_id()` | Effective icon |

### Notes, Efforts, and Attachments

**Notes:**
- Inherit appearance from categories (sorted by stylePriority) then parent notes
- SSOT `effectiveXxx()` methods follow same pattern as Tasks/Categories
- Sources: categories → parent note → default icon (no status)
- Appearance tab shows Derived/Override/Effective sections

**Efforts:**
- NO appearance tab — simple editor without tabs
- Efforts implicitly use the appearance of the task they belong to
- No inheritance model: `shown_*()` return their task's

**Attachments:**
- SSOT `effectiveXxx()` methods (simplest form - override or system theme)
- No inheritance chain - derived is always system theme
- Appearance tab shows Derived/Override/Effective sections

---

## File Reference

| File | Purpose |
|------|---------|
| `taskcoachlib/domain/task/status.py` | TaskStatus class and 6 singleton instances |
| `taskcoachlib/domain/task/task.py` | `computedStatus()`, status styles, `_update_status()` |
| `taskcoachlib/domain/task/filter.py` | ViewFilter with status-based hiding |
| `taskcoachlib/domain/task/tasklist.py` | `nr_of_tasks_per_status()` count method |
| `taskcoachlib/gui/scheduler.py` | GlobalTimer + MasterScheduler |
| `taskcoachlib/gui/dialog/editor.py` | Status display in Edit Task Dates tab |
| `taskcoachlib/gui/viewer/task.py` | Status bar counts, filter UI commands |
| `taskcoachlib/gui/taskbaricon.py` | System tray status counts |
| `taskcoachlib/config/defaults.py` | Default colors, icons, fonts, dueSoonHours |
| `persistence/html/generator.py` | HTML export status CSS |
| `docs/legacy/task_states.dot` | Original 2012 state transition diagram (approximate) |
| `docs/SCHEDULERS.md` | GlobalTimer architecture (drives status updates) |
