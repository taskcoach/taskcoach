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
- `task.computedStatus()` — Returns TaskStatus object (single source of truth) ✓
- `task.statusText()` — Returns display text ✓
- `task.statusIconName()` — Returns icon name ✓
- `task.statusIcon()` — Returns icon name (same as statusIconName, kept for compatibility) ✓
- `task.status()` — Returns TaskStatus object (legacy cached method, to be removed)

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

2. **In progress:** Public accessor `computedStatus()` added. Migrating legacy
   consumers one by one to use `computedStatus()` instead of `status()`:

   | Consumer | File:Line | Status |
   |----------|-----------|--------|
   | ViewFilter.filterTask() | filter.py:153 | ✓ Done |
   | completed() | task.py:615 | ✓ Done |
   | overdue() | task.py:621 | ✓ Done |
   | inactive() | task.py:627 | ✓ Done |
   | active() | task.py:635 | ✓ Done |
   | dueSoon() | task.py:640 | ✓ Done |
   | late() | task.py:645 | ✓ Done |
   | statusFgColor() | task.py:1060 | Pending |
   | statusBgColor() | task.py:1134 | Pending |
   | statusFont() | task.py:1160 | Pending |
   | statusIcon() | task.py:1223 | ✓ Done (now accessor) |
   | nrOfTasksPerStatus() | tasklist.py:31 | Pending |
   | Editor display | editor.py:632 | Pending |

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

## Task Icon Decision Sequence

The task icon displayed in the task list is determined by the following priority sequence.
The first match wins, and the final result is transformed based on whether the task has children.

### Priority Order

```
1. Effort Tracking
   └── If task.isBeingTracked() is True → "clock_icon"
   └── Shown when user is actively tracking time on this task

2. Own Icon Override
   └── task.icon() (non-recursive) - icon set directly on the task
   └── User can set this in the Appearance tab of the task editor

3. Category Icon
   └── categoryIcon() checks:
       a) Each category the task belongs to → category.icon(recursive=True)
       b) If not found, parent task's categoryIcon() (recursive up task tree)
   └── First category with an icon wins

4. Status Icon
   └── statusIcon() returns __status_icon (single source of truth)
   └── Determined by task status: active, inactive, late, duesoon, overdue, completed
   └── Configured in Preferences > Theme > Status Icons
```

### Plural/Singular Transformation

After determining the icon from the priority sequence above, `pluralOrSingularIcon()` is applied.
The transformation depends on whether the task has children AND whether an override is set:

| Has Children | Has Override | Transformation |
|--------------|--------------|----------------|
| Yes | No | Pluralize: `led_blue_icon` → `folder_blue_icon` |
| Yes | Yes | Pluralize: even override icons are transformed |
| No | No | Singularize: `folder_blue_icon` → `led_blue_icon` |
| No | Yes | None: override icon kept as-is |

**Key insight:** Tasks with children ALWAYS show folder icons (even if you set an LED override).
Tasks without children and without override will have folder icons converted back to LEDs.

**Plural mapping (LED → Folder):**

| Input | Output |
|-------|--------|
| `led_blue_icon` | `folder_blue_icon` |
| `led_grey_icon` | `folder_grey_icon` |
| `led_green_icon` | `folder_green_icon` |
| `led_orange_icon` | `folder_orange_icon` |
| `led_purple_icon` | `folder_purple_icon` |
| `led_red_icon` | `folder_red_icon` |
| `led_yellow_icon` | `folder_yellow_icon` |
| `checkmark_green_icon` | `checkmark_green_icon_multiple` |

**Singular mapping (Folder → LED):** The reverse of the above.

### Computed vs Final Icon

| Term | Definition | Storage |
|------|------------|---------|
| **Status Icon** | Icon based on task status alone | `__status_icon` (single source of truth) |
| **Computed Icon** | `categoryIcon() or statusIcon()` (before override) | `__recursiveIcon` |
| **Final Icon** | Full cascade result including override + plural/singular | Computed on-the-fly by `icon(recursive=True)` |

**Note:** The final icon is currently computed on-the-fly, not stored. This could be refactored to use a single source of truth pattern.

---

## Appearance Inheritance

Both Tasks and Categories support appearance inheritance (icon, foreground color, background color, font).
The Appearance tab in the editor shows two sections: **Derived values** and **Override values**.

### Task Appearance

Tasks **always** have derived values because they always have a status. The inheritance cascade is:

```
Derived values (read-only display):
├── Icon: categoryIcon() or statusIcon()
├── Foreground: categoryForegroundColor() or statusFgColor()
└── Background: categoryBackgroundColor() or statusBgColor()

Override values (editable):
├── Icon: own icon set directly on task
├── Foreground: own foreground color
├── Background: own background color
└── Font: own font
```

The status always provides a fallback, so derived values are never empty for tasks.

### Category Appearance

Categories inherit appearance from their **parent category**. If no parent exists or the parent has no value, "N/A" is displayed.

```
Derived values (read-only display):
├── Icon: parent.icon(recursive=True) or "N/A"
├── Foreground: parent.foregroundColor(recursive=True) or "N/A"
└── Background: parent.backgroundColor(recursive=True) or "N/A"

Override values (editable):
├── Icon: own icon set directly on category
├── Foreground: own foreground color
├── Background: own background color
└── Font: own font
```

#### Effective Appearance Fields (Single Source of Truth)

**File:** `taskcoachlib/domain/category/category.py`

Categories now have **effective appearance fields** that store the final computed value:

| Field | Accessor | Value |
|-------|----------|-------|
| `__effective_fg_color` | `effectiveFgColor()` | Own override OR parent's effective |
| `__effective_bg_color` | `effectiveBgColor()` | Own override OR parent's effective |
| `__effective_icon` | `effectiveIcon()` | Own override OR parent's effective |
| `__effective_font` | `effectiveFont()` | Own override OR parent's effective |

**How it works:**

1. **Computation:** `_computeEffectiveAppearance()` computes effective values from:
   - Own override if set (via `foregroundColor(recursive=False)`, etc.)
   - Otherwise, parent's effective value (via `parent.effectiveFgColor()`, etc.)

2. **Update triggers:**
   - On category creation (`__init__`)
   - When appearance changes (`appearanceChangedEvent`)

3. **Automatic propagation:** When a parent's appearance changes, `appearanceChangedEvent` cascades to all children (via `CompositeObject.appearanceChangedEvent`), causing each child to recompute its effective values.

```
Parent category appearance changes
    └── appearanceChangedEvent(event)
        ├── _computeEffectiveAppearance()  ← Recompute own effective values
        ├── super().appearanceChangedEvent(event)
        │   └── for child in children():
        │       └── child.appearanceChangedEvent(event)  ← Children recompute
        └── for categorizable in categorizables():
            └── categorizable.appearanceChangedEvent(event)  ← Tasks notified
```

**Benefits:**
- Single source of truth: `effectiveXxx()` returns the final value directly
- No recursive lookup at query time: value is pre-computed
- Automatic updates: pub/sub propagation ensures children stay in sync
- Parent is authoritative: children derive from parent's effective value

#### Legacy Code Compatibility

**IMPORTANT:** The legacy `recursive=True` parameter on `foregroundColor()`, `backgroundColor()`, `icon()`, and `font()` is **preserved for backward compatibility**. Do not modify the legacy methods in `CompositeObject`.

| Method | Behavior |
|--------|----------|
| `foregroundColor(recursive=True)` | **Legacy** — walks up parent chain at query time |
| `effectiveFgColor()` | **New** — returns pre-computed effective value |

New code should use the `effectiveXxx()` methods. Legacy code continues to work unchanged.

#### TODO: Implement for Tasks

**Status:** Pending

Tasks also need effective appearance fields following the same pattern as Categories.

**Task Appearance Cascade (priority order):**

```
1. Own override (task's own icon/fg/bg/font)
   └── If set, use it

2. Task's direct categories
   └── Use category.effectiveIcon() / effectiveFgColor() / etc.
   └── No recursion needed - category already has pre-computed effective value
   └── If multiple categories: mix colors, first icon wins

3. Parent task's category (if child task has NO direct categories)
   └── Child task asks parent._categoryForegroundColor()
   └── Parent returns its category's effective value
   └── This is how category appearance flows from parent task to child task

4. Status appearance (fallback - task always has a status)
   └── statusIcon(), statusFgColor(), statusBgColor()
```

**Key simplification:** Since categories now have `effectiveXxx()` methods, the task code can call those directly instead of `category.foregroundColor(recursive=True)`. The category has already computed its effective value from its own parent chain.

**Task-to-task inheritance:** When a child task has no categories but its parent task does, the child inherits the category appearance via the parent task (not directly from the category). The parent task returns its category's effective value.

**Implementation steps:**
- Add `__effective_fg_color`, `__effective_bg_color`, `__effective_icon`, `__effective_font` fields to Task
- Add `effectiveFgColor()`, `effectiveBgColor()`, `effectiveIcon()`, `effectiveFont()` accessors
- Add `_computeEffectiveAppearance()` method implementing the cascade above
- Update `_categoryForegroundColor()` etc. to use `category.effectiveXxx()` instead of `recursive=True`
- Call from `__init__`, `recomputeAppearance()`, and when categories change
- Update Appearance tab to show Effective section for tasks

### Inheritance Methods

**File:** `taskcoachlib/domain/base/object.py`

| Method | Behavior |
|--------|----------|
| `foregroundColor(recursive=False)` | Own color only |
| `foregroundColor(recursive=True)` | Own color, or parent's recursive color |
| `backgroundColor(recursive=False)` | Own color only |
| `backgroundColor(recursive=True)` | Own color, or parent's recursive color |
| `icon(recursive=False)` | Own icon only |
| `icon(recursive=True)` | Own icon, or parent's recursive icon, then plural/singular transform |
| `font(recursive=False)` | Own font only |
| `font(recursive=True)` | Own font, or parent's recursive font |

### Notes and Attachments

Notes and Attachments do not show derived/override sections in the Appearance tab because they have no status and no category inheritance chain. They only have their own appearance settings.

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
