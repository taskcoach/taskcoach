# Task Status System

## Index

1. [Overview](#overview)
2. [Status Values](#status-values)
   - [Encoding](#encoding)
   - [Identity and Comparison](#identity-and-comparison)
3. [State Transitions](#state-transitions)
4. [Architecture](#architecture)
   - [Stored Fields](#stored-fields)
   - [computeStatus() — Single Source of Truth](#computestatus--single-source-of-truth-class-method)
   - [computeStoredStatus() — Instance Update Method](#computestoredstatus--instance-update-method)
   - [Editor Live Preview](#editor-live-preview)
   - [Event: statusChangedEventType](#event-statuschangedeventtype)
   - [Update Triggers](#update-triggers)
   - [Timer-Driven Updates (ComputeStyles)](#timer-driven-updates-computestyles)
   - [Immediate Updates (Date Setters)](#immediate-updates-date-setters)
   - [Viewer Columns](#viewer-columns)
5. [Usage Locations](#usage-locations)
   - [Sources of Truth](#sources-of-truth)
   - [Consumers](#consumers-read-taskstatus-cache)
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
   - [Plural/Singular Transformation](#pluralsingular-transformation)
   - [Computed vs Final Icon](#computed-vs-final-icon)
10. [Appearance Inheritance](#appearance-inheritance)
    - [Appearance Tab Layout (3-Column Grid)](#appearance-tab-layout-3-column-grid)
    - [Task Appearance](#task-appearance)
    - [Category Appearance](#category-appearance)
    - [Inheritance Methods](#inheritance-methods)
    - [Notes and Attachments](#notes-and-attachments)
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

`computedStatus()` is cached and only updated by the scheduler (every second). During event handlers, it may be **stale**.

```python
# BAD - uses stale cache during event handler:
def completed(self):
    return self.computedStatus() == status.completed

# GOOD - direct SSOT check, always accurate:
def completed(self):
    return self.completionDateTime() != self.maxDateTime
```

### Example: Cascade Bug

When child task is completed, `_onCompletionDateTimeChanged` fires. At that moment:
- Child's `completionDateTime` is set (accurate)
- Child's `computedStatus()` is stale (not yet recomputed)
- Parent calls `allChildrenCompleted()` → `child.completed()` → returns False!

**Fix:** `completed()` must use direct datetime check, not `computedStatus()`.

### Rule

Action methods (`completed()`, `allChildrenCompleted()`, etc.) must use **direct field checks**. The computed status system is for display/reporting only.

---

## Appearance Inheritance Overview

### ComputeStyles Polling (New Architecture)

The appearance SSOT system now uses **per-second polling** via `ComputeStyles` class instead of
trigger-based updates. This provides:

1. **Eventual consistency** - All changes detected within 1-2 seconds
2. **Simplified architecture** - No need to track all possible triggers
3. **Catches time-based changes** - Status changes from time passing are automatically detected

**Processing order:** Categories → Tasks → Notes → Attachments

**Key classes:**
- `MasterScheduler` in `scheduler.py` - Polls every second, calls `computeStyles()` for each object
- `computeDerived(obj, field_type)` - Computes derived value from sources
- `computeEffective(obj, field_type)` - Computes effective from override + derived

**Category stylePriority:**
Tasks with multiple categories use `stylePriority` to determine which category's style wins.
Higher priority wins. Default is 0.

### Object Type Summary

| Object Type | Derived From | SSOT Methods | Appearance Tab |
|-------------|--------------|--------------|----------------|
| **Task** | Categories → Parent task → Status | `effectiveXxx()` | Yes |
| **Category** | Parent category → System Theme | `effectiveXxx()` | Yes |
| **Note** | Parent note → System Theme | `effectiveXxx()` | Yes |
| **Attachment** | System Theme only (no inheritance) | `effectiveXxx()` | Yes |
| **Effort** | Task (always) | None | **No** - uses task's appearance |

**Key points:**
- All object types with appearance tabs have SSOT `effectiveXxx()` and `derivedXxx()` methods
- Complexity varies: Tasks have most sources, Attachments have fewest (just override or system theme)
- Notes inherit from parent notes only (do NOT inherit from attached task)
- Efforts have no appearance tab; they always display using their task's appearance

**"Nothing Set" Convention:**
- Colors/Fonts: `None` = nothing set (default in `object.py`)
- Icons: `""` (empty string) = nothing set (default in `object.py`)
- Both are **falsy** in Python, so `if value:` works for both
- Do NOT interchange — icon code uses explicit `== ""` checks for plural/singular logic

**System Theme Constants:**
- `base.SYSTEM_FG_COLOR` = "SYS_COLOUR_WINDOWTEXT"
- `base.SYSTEM_BG_COLOR` = "SYS_COLOUR_WINDOW"
- `base.SYSTEM_FONT` = "SYS_DEFAULT_GUI_FONT"
- `base.SYSTEM_THEME_SOURCE` = "System Theme"
- **Icons have no system theme** — use `""` when no value, UI shows "N/A"

**SSOT Method Contract:**

**Effective accessors** use separate methods:

| Call | Returns | Purpose |
|------|---------|---------|
| `effectiveXxx()` | value | Actual value (None/"" if nothing set) |
| `effectiveXxxDefault()` | default | System theme constant to use when value is empty |
| `effectiveXxxSource()` | source | "Override", "[Category] Name", etc. |

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
    """Return effective foreground color source ("Override", "[Category] Name", etc)."""
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
- **computeDerived()** in `appearance.py` computes and writes to SSOT
- **computeEffective()** in `appearance.py` computes effective from derived + override
- UI resolves: `color = resolve_color(actual if actual else default)`

**TODO — Refactor plural/singular icon logic:**
- Current code in `object.py` and `task.py` uses brittle `native=super().icon() == ""`
- This checks if icon is "native" (not user-overridden) for folder/LED transformation
- Should be refactored to use a cleaner API (e.g., `hasIconOverride()` method)
- Blocked on: completing SSOT 3-tuple refactor first

---

## Overview

Task status is a dynamically computed property of each task, derived from the task's date fields and the current time. It determines the task's visual appearance (color, icon, font) and is used for filtering, status bar counts, system tray tooltips, and HTML export styling.

**See also:**
- `docs/SCHEDULERS.md` — GlobalTimer architecture (the single main loop that drives status updates)
- `docs/ICON_LIBRARY.md` — Icon sources, structure, and adding new icons
- `docs/ICON_PLURALIZE.md` — Plural/singular icon mapping
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

### computeStatus() — Single Source of Truth (Class Method)

**File:** `taskcoachlib/domain/task/task.py`

The `Task.computeStatus()` class method is the **single source of truth** for status calculation.
It takes date values as parameters and returns `(TaskStatus, source_string)` tuple.

```python
@classmethod
def computeStatus(cls, completionDT, dueDT, actualStartDT, plannedStartDT,
                  dueSoonHours, hasIncompletePrerequisites, now=None,
                  maxDateTime=None):
    """Compute task status from date values. SINGLE SOURCE OF TRUTH."""
    # Priority order: completed > inactive(prereqs) > overdue > duesoon > active > late > inactive
    if completionDT != maxDateTime:
        return status.completed, _("Completion date is set")
    if hasIncompletePrerequisites:
        return status.inactive, _("Has incomplete prerequisites")
    if dueDT != maxDateTime and dueDT < now:
        return status.overdue, _("Due date has passed")
    # ... etc
    return status.inactive, _("No actual start date")
```

### computeStoredStatus() — Instance Update Method

The `task.computeStoredStatus()` instance method calls `computeStatus()` with the task's
actual values and stores the results in the task's fields.

Called from:
- `Task.__init__()` — Initial population on task creation/load
- `recomputeAppearance()` — Immediate update on date changes (called by all date setters)
- `ComputeStyles._computeForObject()` — Called per-task before `computeDerived()` and `computeEffective()`, ensuring status is fresh before appearance computation

### Editor Live Preview

The editor's `_computeLocalStatus()` method also calls `Task.computeStatus()`, but passes
form field values instead of the task's stored values. This enables live preview as the
user edits dates before committing changes.

### Event: statusChangedEventType

`task.Task.statusChangedEventType()` returns `"pubsub.task.status"`

Fired by `computeStatus()` only when status actually changes.
Subscribers: status columns in TaskViewer (via column event infrastructure).

### Update Triggers

Status is recomputed in three scenarios:

1. **On load** — `Task.__init__()` calls `computeStatus()` once
2. **On date change** — Date setters (e.g., `setDueDateTime()`) call `recomputeAppearance()` which calls `computeStatus()` at its start. This provides immediate status updates.
3. **Every second** — `ComputeStyles._computeForObject()` calls `computeStoredStatus()` for each task as part of its per-object processing pass, ensuring status is fresh before computing derived and effective appearance values.

### Timer-Driven Updates (ComputeStyles)

**File:** `taskcoachlib/gui/scheduler.py`
**Instantiated in:** `taskcoachlib/gui/mainwindow.py:_create_window_components()`

`MasterScheduler` subscribes to `timer.second` (the GlobalTimer's 1-second tick) and
processes all objects. For each task, the per-object flow is:

```
GlobalTimer._onTick() (every 1 second)
    └── pub.sendMessage('timer.second', timestamp=now)
        └── MasterScheduler._onSecond(timestamp)
            └── For each task:
                1. task.computeStoredStatus()
                │   ├── Calls Task.computeStatus() with task's dates
                │   ├── Updates __computed_status, __status_text, __status_icon
                │   └── Fires statusChangedEventType if changed
                2. computeStyles(task)
                    ├── computeDerived(task, field_type) for each field
                    └── computeEffective(task, field_type) for each field
```

See docs/SCHEDULERS.md for the complete MasterScheduler processing flow.

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

| Location | File | Source of Truth | What It Does |
|----------|------|-----------------|--------------|
| Core calculation | `domain/task/task.py` | Dates + now + dueSoonHours | Computes and caches status |
| ComputeStyles | `domain/base/appearance.py` | Calls `computeStoredStatus()` per task | Computes status then derived/effective appearance per object |
| Editor live preview | `gui/dialog/editor.py` | **Duplicates date logic** | Computes status from form field values |

### Consumers (read task.status() cache)

| Consumer | File | Purpose |
|----------|------|---------|
| Status helper methods | `domain/task/task.py` | `completed()`, `overdue()`, `active()`, etc. |
| Color cascade | `domain/task/task.py` | Foreground color fallback (own > category > status) |
| Background cascade | `domain/task/task.py` | Background color fallback |
| Font cascade | `domain/task/task.py` | Font fallback |
| Icon cascade | `domain/task/task.py` | Icon fallback |
| ViewFilter | `domain/task/filter.py` | Hide tasks by status |
| Status bar | `gui/viewer/task.py` | Task count per status |
| Task list counts | `domain/task/tasklist.py` | `nrOfTasksPerStatus()` |
| Taskbar tooltip | `gui/taskbaricon.py` | System tray overdue/duesoon counts |
| Editor display | `gui/dialog/editor.py` | Shows icon + colored text in Dates tab |
| HTML export | `persistence/html/generator.py` | CSS class per status |

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

### 1. Duplicated Calculation Logic — RESOLVED

**Status:** Complete. Single source of truth implemented.

The status calculation now exists in **one place only**:

- **`Task.computeStatus()`** — class method, single source of truth

All other code calls this method:
- **`task.computeStoredStatus()`** — instance method that calls `computeStatus()` and stores results
- **`DatesPage._computeLocalStatus()`** — calls `Task.computeStatus()` with form field values for live preview
- **`ComputeStyles._computeForObject()`** — calls `task.computeStoredStatus()` for each task during per-object processing

The `computeStatus()` method returns `(TaskStatus, source_string)` tuple, providing both the status and an explanation of why the task has that status.

### 2. No Dedicated Status Event — RESOLVED

`statusChangedEventType` (`"pubsub.task.status"`) now exists, fired by `computeStatus()` only on actual transitions. The new status columns subscribe to it.
Legacy consumers still use `appearanceChangedEventType()` as a proxy.

### 3. StatusChecker Duplicates Logic — RESOLVED

StatusChecker has been merged into ComputeStyles. Each task's `computeStoredStatus()` is
now called directly within `ComputeStyles._computeForObject()`, immediately before
`computeDerived()` and `computeEffective()`. This eliminates the duplicated date logic
and guarantees correct ordering: status is always fresh when appearance values are computed.

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

   | Consumer | File | Status |
   |----------|------|--------|
   | ViewFilter.filterTask() | filter.py | ✓ Done |
   | completed() | task.py | ✓ Done |
   | overdue() | task.py | ✓ Done |
   | inactive() | task.py | ✓ Done |
   | active() | task.py | ✓ Done |
   | dueSoon() | task.py | ✓ Done |
   | late() | task.py | ✓ Done |
   | statusFgColor() | task.py | Pending |
   | statusBgColor() | task.py | Pending |
   | statusFont() | task.py | Pending |
   | statusIcon() | task.py | ✓ Done (now accessor) |
   | nrOfTasksPerStatus() | tasklist.py | Pending |
   | Editor display | editor.py | ✓ Done (uses derivedXxx/effectiveXxx) |
   | Appearance tab 3-col layout | editor.py | ✓ Done |
   | Task derivedXxx(explain) | task.py | ✓ Done |
   | Task effectiveXxx(explain) | task.py | ✓ Done |
   | Category derivedXxx(explain) | category.py | ✓ Done |
   | Category effectiveXxx(explain) | category.py | ✓ Done |
   | computeStatus() centralized | task.py | ✓ Done (class method, no duplication) |
   | computedStatus(explain) | task.py | ✓ Done |
   | Dates tab status source | editor.py | ✓ Done (uses Task.computeStatus) |
   | Font picker preview colors | editor.py | ✓ Done (uses effectiveFgColor/effectiveBgColor) |
   | Path tab icons | editor.py | ✓ Done (uses effectiveIcon) |
   | Category cascade on load | category.py | ✓ Done (centralized in _computeEffectiveAppearance) |
   | Note effectiveXxx(explain) | note.py | ✓ Done |
   | Attachment effectiveXxx(explain) | attachment.py | ✓ Done |

3. **Final cleanup:** Remove legacy `status()` cache, `__status` field, and the
   scattered `__status = None` invalidations. Remove duplicated logic from
   `DatesPage._computeLocalStatus()`.

### Staleness Tradeoff — RESOLVED

Immediate updates are now implemented: `recomputeAppearance()` (called by all date
setters) invokes `computeStatus()` at its start. This means:
- User-driven date changes → instant status update (no 1-second delay)
- Time-based transitions → detected within 1 second by ComputeStyles
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

> Full mapping tables and all callers: [ICON_PLURALIZE.md](ICON_PLURALIZE.md)

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
Icon          [bitmap]           Override
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
- `[Category] Name` — from a category
- `[Task] Name` — from parent task
- `[Note] Name` — from parent note
- `[Status] StatusName` — from task status (e.g., Inactive, Active, Overdue)
- `Override` — user set this value
- `System Theme` — no value set, using system default (colors/fonts only)
- `N/A` — no derived value (icons only - there is no "system theme" for icons)

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

Categories inherit appearance from their **parent category**.

Derived values are computed by `computeDerived()` and stored as SSOT Attribute fields.
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
These are written by `computeDerived()` and `computeEffective()` stored procedures, called
by the `ComputeStyles` per-second poller.

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

#### Stored Procedure: computeDerived

```
computeDerived(object_ref, field_type)

INPUTS:  object_ref (domain object), field_type ('fgColor', 'bgColor', 'font', 'icon')
OUTPUTS: calls object's setDerivedXxx(value, source) Attribute setter
```

**Behavior:**
1. Determine object type (Task, Category, Note, Attachment)
2. For Tasks: check categories → parent task → status (in priority order)
3. For Categories/Notes: check parent's effective value
4. Write via object's Attribute-based setter (fires change event automatically)

**Called by:** `ComputeStyles` per-second poller

---

#### Stored Procedure: computeEffective

```
computeEffective(object_ref, field_type)

INPUTS:  _derived_{field}_value, _derived_{field}_source, override value
OUTPUTS: _effective_{field}_value, _effective_{field}_default, _effective_{field}_source
```

**Behavior:**
1. Read derived value/source from object's Attribute getters
2. Read override value from object's override getter
3. Compute: `effective = override if override else derived`
4. Write via object's Attribute-based setter (fires change event automatically)

**Called by:** `ComputeStyles` per-second poller

---

#### Pattern

ComputeStyles polling pattern (eventual consistency):
1. User changes override value (or category assignment, status, etc.)
2. ComputeStyles poller runs every second
3. For each object: `computeDerived()` then `computeEffective()` for each field type
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

#### Update Mechanism: ComputeStyles Polling

**No triggers or explicit cascade needed.** The `ComputeStyles` class polls every second:

```
ComputeStyles (per-second polling)
  └── For each object in taskFile (tasks, categories, notes, attachments):
      └── For each field_type in ('fgColor', 'bgColor', 'font', 'icon'):
          1. computeDerived(object, field_type)
          2. computeEffective(object, field_type)
```

This catches ALL changes without explicit triggers:
- Category assignment/removal
- Parent relationship changes
- Status changes (time-based transitions)
- Override value changes
- File load (volatile fields populated within 1 second)

**No post-load initialization needed** — ComputeStyles polling handles it.

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
3. Fire pubsub ONLY if output changed (for UI refresh)

---

#### Volatile Fields

**SSOT fields are volatile** — they are NOT persisted to the task file.
See ATTRIBUTE_PATTERN.md §Volatile vs Persisted Attributes for the general pattern.

The derived and effective Attribute fields are:
- **Not in `__getstate__()`** — excluded from serialization
- **Initialized to None/""** after file load
- **Populated by ComputeStyles polling** within 1 second of app start

**Why volatile?**
- Effective values are computed from persisted data (overrides, parent relationships)
- No need to persist what can be recomputed
- Reduces file size and avoids stale value problems

**No post-load initialization needed** — `ComputeStyles` polling replaces all
post-load handlers. The poller runs every second and populates all volatile
fields automatically.

---

#### Data Flow (SSOT Principle)

**Attribute fields defined in object.py** — derived and effective values are Attribute objects
with automatic change event firing via `Attribute.set()`.

**Application startup / file load sequence:**

```
1. App starts, loads data file
   └── Objects created with override values, parent relationships

2. MasterScheduler starts (timer.second)
   └── Within 1 second, all objects get status + derived + effective values computed

3. Ongoing: scheduler runs every second
   └── Any data change (override, category, status, parent) is picked up
   └── Attribute.set() fires per-field change events when values change
   └── UI subscribers update automatically
```

**Key insight:** No explicit triggers needed. The per-second poll catches all changes
with eventual consistency (1-2 second latency).

---

**Data Model Storage:**

Appearance values stored as `Attribute` objects on base `Object` class in `object.py`.
Each Attribute fires a change event when its value is set via `Attribute.set()`
(see ATTRIBUTE_PATTERN.md for the Attribute API).

```
Derived (Attribute fields, written by computeDerived):
  _derived_fgColor       (value)    _derived_fgColor_source
  _derived_bgColor       (value)    _derived_bgColor_source
  _derived_font          (value)    _derived_font_source
  _derived_icon          (value)    _derived_icon_source

Effective (Attribute fields, written by computeEffective):
  _effective_fgColor     (value)    _effective_fgColor_default    _effective_fgColor_source
  _effective_bgColor     (value)    _effective_bgColor_default    _effective_bgColor_source
  _effective_font        (value)    _effective_font_default       _effective_font_source
  _effective_icon        (value)    — (no default for icons)      _effective_icon_source
```

Accessor methods are generated by Attribute fields and return stored values directly.

---

**Change Detection:**

1. ComputeStyles poller runs every second
2. Calls `computeDerived()` and `computeEffective()` for all objects
3. `Attribute.set()` compares new vs prior value (see ATTRIBUTE_PATTERN.md)
4. If changed: fires per-field change event (e.g., `derivedFgColorChangedEventType()`)
5. UI subscribers update display

**Self-limiting:** Attribute.set() only fires events when value actually changes.

**Benefits:**
- **Universal:** One poller handles all object types and all change sources
- **No triggers needed:** Catches time-based transitions, category changes, parent changes, etc.
- **Eventual consistency:** 1-2 second latency, acceptable for appearance updates
- **Simple:** No complex trigger/cascade logic to maintain

#### Legacy Code Compatibility

**IMPORTANT:** The legacy `recursive=True` parameter on `foregroundColor()`, `backgroundColor()`, `icon()`, and `font()` is **preserved for backward compatibility**. Do not modify the legacy methods in `CompositeObject`.

| Method | Behavior |
|--------|----------|
| `foregroundColor(recursive=True)` | **Legacy** — walks up parent chain at query time |
| `effectiveFgColor()` | **New** — returns pre-computed effective value |

New code should use the `effectiveXxx()` methods. Legacy code continues to work unchanged.

#### Task Effective Appearance

Tasks have `derivedXxx()` / `derivedXxxSource()` and `effectiveXxx()` / `effectiveXxxSource()` accessor methods.

**Task Appearance Cascade (priority order) — computed by `computeDerived()`:**

```
1. Task's direct categories
   └── Use category.effectiveFgColor() etc.
   └── Source: "[Category] CategoryName"

2. Parent task's effective value (if child task has NO direct categories)
   └── Child task asks parent.effectiveFgColor() etc.
   └── Source: "[Task] ParentTaskName"

3. Status appearance (fallback - task always has a status)
   └── statusIcon(), statusFgColor(), statusBgColor()
   └── Source: "[Status] StatusName" (e.g., "[Status] Inactive", "[Status] Active")
```

**`effectiveXxx()` is simple:** own override OR derivedXxx()
- If own override set → Source: "Override"
- Else → delegates to `derivedXxx()`

**SSOT accessors** (defined as Attribute fields in base `Object`, written by `computeDerived()` and `computeEffective()`):

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
- `"Override"` — user set this value directly
- `"[Category] WorkCategory"` — from a category's effective value
- `"[Task] ParentTaskName"` — from parent task's effective value
- `"[Status] Inactive"` — from task status (includes status name)
- `"System Theme"` — (Categories/Notes/Attachments only, not Tasks)

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

### Notes, Efforts, and Attachments

**Notes:**
- Inherit appearance from categories (sorted by stylePriority) then parent notes
- SSOT `effectiveXxx()` methods follow same pattern as Tasks/Categories
- Sources: categories → parent note → default icon (no status)
- Appearance tab shows Derived/Override/Effective sections

**Efforts:**
- NO appearance tab — simple editor without tabs
- Efforts implicitly use the appearance of the task they belong to
- No inheritance model — appearance comes directly from task

**Attachments:**
- SSOT `effectiveXxx()` methods (simplest form - override or system theme)
- No inheritance chain - derived is always system theme
- Appearance tab shows Derived/Override/Effective sections

---

## File Reference

| File | Purpose |
|------|---------|
| `taskcoachlib/domain/task/status.py` | TaskStatus class and 6 singleton instances |
| `taskcoachlib/domain/task/task.py` | `status()`, color/icon/font methods, `recomputeAppearance()` |
| `taskcoachlib/domain/task/filter.py` | ViewFilter with status-based hiding |
| `taskcoachlib/domain/task/tasklist.py` | `nrOfTasksPerStatus()` count method |
| `taskcoachlib/gui/scheduler.py` | GlobalTimer + MasterScheduler |
| `taskcoachlib/gui/dialog/editor.py` | Status display in Edit Task Dates tab |
| `taskcoachlib/gui/viewer/task.py` | Status bar counts, filter UI commands |
| `taskcoachlib/gui/taskbaricon.py` | System tray status counts |
| `taskcoachlib/config/defaults.py` | Default colors, icons, fonts, dueSoonHours |
| `persistence/html/generator.py` | HTML export status CSS |
| `docs/legacy/task_states.dot` | Original 2012 state transition diagram (approximate) |
| `docs/SCHEDULERS.md` | GlobalTimer architecture (drives status updates) |
