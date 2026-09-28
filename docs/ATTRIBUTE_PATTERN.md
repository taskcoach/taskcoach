# Attribute Pattern

The domain model's change-detection and event-notification pattern.

## Index

- [TODO](#todo)
- [Signal Dispatch](#signal-dispatch)
  - [Case Study: Tree Mode Toggle](#case-study-tree-mode-toggle)
- [Overview](#overview)
- [Attribute Class API](#attribute-class-api)
- [SetAttribute Class API](#setattribute-class-api)
- [Value Normalization](#value-normalization)
  - [Dates: Not Set Is the Latest Date](#dates-not-set-is-the-latest-date)
- [Setter / Callback Pattern](#setter--callback-pattern)
- [Event Batching During Load](#event-batching-during-load)
- [Volatile vs Persisted Attributes](#volatile-vs-persisted-attributes)
- [Modification Date](#modification-date)
- [Three-Layer Relationship](#three-layer-relationship)

---

## TODO

1. **Migrate remaining `EVT_KILL_FOCUS` AttributeSync sites to
   `EVT_VALUE_CHANGED`.** The legacy pattern binds AttributeSync to
   `EVT_KILL_FOCUS` (blur). This works for user edits but is invisible
   to programmatic writes — widget methods like `SetDuration()` fire
   `EVT_VALUE_CHANGED`, not `EVT_KILL_FOCUS`, so the AttributeSync
   never sees them and the domain is never updated.
   **Done:** All `MaskedFieldsCtrl`-based controls — DurationCtrl (task
   and effort), budget (`MaskedDurationCtrl`), all DateTimeComboCtrl fields,
   hourly fee, and fixed fee now use `EVT_VALUE_CHANGED` with immediate
   commit. `MaskedFieldsCtrl` fires only on blur (user) or
   `SetDuration()`/`SetTime()`/`SetDate()` (programmatic).
   **Remaining:** subject, description, and attachment location use
   `wx.TextCtrl` (fires per-keystroke `EVT_TEXT`) — different migration
   path. See
   [Three-Layer Relationship](#three-layer-relationship), Layer 2.

2. **Migrate signal dispatch to per-instance.** See
   [PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#todo) for full status,
   done/remaining items, and migration plan.

3. **Modularize and clean up the signaling system.** See
   [PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#signaling-system-cleanup)
   for full status, done/remaining items, and cleanup plan.

---

## Signal Dispatch

See [PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#signal-dispatch) for the
full signal dispatch architecture, pypubsub migration plan, and naming
convention.

### Case Study: Tree Mode Toggle

See [PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#case-study-tree-mode-toggle).

---

## Overview

`Attribute` wraps a domain field value with:

1. **Equality check** — `.set()` compares new vs current value; no-ops if unchanged
2. **Event notification** — fires a callback only when value actually changes
3. **Consistent API** — `.get()` / `.set(value, event=None)`

The standard pattern for all domain fields — both persisted and volatile.

The domain model is an **in-memory SSOT**. `.set()` updates the value
immediately — there is no commit/rollback. All subsequent operations in the
callback — dirty-flagging, appearance recomputation, notifications — read
from the already-updated in-memory state. The order between these operations
does not matter because they all see the same current truth. Persistence to
disk is a separate concern, triggered by an explicit save command.

**File:** `taskcoachlib/domain/base/attribute.py`

---

## Attribute Class API

**Key properties:**

- `.get()` returns the stored value
- `.set(value, event=None)` compares new vs current:
  - Unchanged → returns `False`, no callback, no event
  - Changed → stores value, calls `setEvent(owner, event)`, returns `True`
- `setEvent` fires inside the `@patterns.eventSource` decorator, so events
  batch correctly during `__setstate__`
- Owner stored as `weakref` — no circular reference issues

**See:** `taskcoachlib/domain/base/attribute.py` for implementation.

---

## SetAttribute Class API

For collection-valued fields (sets of categories, prerequisites, etc.).
Same equality-check principle: `.set()` no-ops if the new set equals the
current set. Separate callbacks for add, remove, and change operations.

**See:** `taskcoachlib/domain/base/attribute.py` for implementation.

---

## Value Normalization

**General strategy:** All Attribute fields normalize invalid, missing, zero,
or sentinel values to one value per logical state at the boundary
(constructor, setter entry, XML load): `None`, except for dates, whose
"not set" is the latest date
([below](#dates-not-set-is-the-latest-date)). This guarantees equal
values for equal states in the equality check.

| Raw Value | Normalized | Rationale |
|-----------|-----------|-----------|
| `TimeDelta()` (zero duration) | `None` | "no duration set" |
| Date not set | `date.DateTime()`, the latest date | "no date set": [see below](#dates-not-set-is-the-latest-date) |
| Missing from XML / state dict | `None` | Field not present |
| `""` or invalid value for mode/enum fields | `None` | "no mode set" — not a silent fallback |

Without normalization, the same logical state ("not set") can have multiple
representations (zero, sentinel, None, empty string). The Attribute equality
check only works reliably when the same logical state always has the same value.

Normalization happens in the **setter**, before calling `.set()`.
Example: `setPlannedDurationMode()` maps old mode names and rejects
invalid values to `None` before delegating to the Attribute.

### Dates: Not Set Is the Latest Date

A task's planned start, due, actual start, completion and reminder are
optional. "Not set" is the latest date, `date.DateTime()`: 9999-12-31
23:59:59, the latest whole second (dates are whole seconds:
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#time-resolution)).
The same value is also named `DateTime.max` and `Task.maxDateTime`.

It plays two roles at once:

- **Not set.** Shown blank; the date picker unchecked (its `GetValue()`
  returns it when unchecked, and `SetValue()` takes it or `None` as
  unchecked, [DATETIME_CONTROLS.md](DATETIME_CONTROLS.md)); not written
  to the file, and a missing attribute reads back as it
  ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#writer-skip-conditions));
  skipped by exports. A task whose completion date is not set is not
  completed.
- **Never, infinitely far.** Being the latest date, it makes plain time
  comparisons right without an "is it set?" case: an unset due date is
  never passed (never overdue), an unset planned start never reached
  (never late); tasks without a date sort last; the earliest due date
  of the subtasks (`min`) ignores unset ones; the time left is
  infinite (`TimeDelta.max`); an effort still running sorts as stopping
  at the end of time.

Why not `None`: it would split the two roles, and every comparison
(status rules, sorting, earliest due date, time left) would need its
own "is it set?" branch. The latest date gives the "never" behaviour
from ordinary comparisons.

A date typed in the picker as 9999-12-31 23:59:59 is this value: it
shows blank and is not saved, and it means "never" either way.

`DateTime.min`, the earliest date, is the counterpart for an unknown
creation or modification time, from old files.

The setters store it for `None`: `setPlannedStartDateTime()`,
`setDueDateTime()`, `setActualStartDateTime()` and `setReminder()`
take `None` as "not set". `setCompletionDateTime()` differs by design:
without a date it means now (mark completed), and the latest date
reopens the task. Over subtasks, the planned start, actual start, due
and reminder take the earliest date, so unset ones never win; the
completion takes the latest, so a parent not completed stays not set.

Until 2026-09-27 the reminder also used `None` ("not set" after
clearing or snoozing without a delay); it now uses the latest date as
every other date.

One place still uses `None`, for a different meaning: an effort still
being tracked has no stop yet (`Effort.getStop()` is `None`), and
comparisons map it to the latest date. Efforts are not in the master
timer list, so it is left as is.

---

## Setter / Callback Pattern

Clean separation between the setter and the callback:

- **Setter** — normalizes input and calls `.set()`. Knows nothing about
  business rules. One or two lines.
- **Callback** — contains ALL business logic. Fires only when the value
  actually changes. Reads from the in-memory SSOT (the Attribute already
  stores the new value before the callback runs).
- **Attribute** — handles equality check, storage, and firing the callback.

Three complexity levels of callbacks:

**Notification callback** — fires change signal (see
[PUBLISHER_OBSERVER.md — Signal Dispatch](PUBLISHER_OBSERVER.md#signal-dispatch)), `markDirty`,
`recomputeAppearance`. Example: `_onDueDateTimeChanged`,
`_onPlannedStartDateTimeChanged`.

**Cross-field callback** — reacts to current state and triggers other
setters. Example: `_onPercentageCompleteChanged` triggers
`setCompletionDateTime` or `setActualStartDateTime` based on the new
percentage value and current state.

**Re-entrant callback** — when a callback triggers another setter (e.g.
`_onCompletionDateTimeChanged` → `recur()` → `setCompletionDateTime(maxDateTime)`),
the Attribute equality check prevents infinite loops. The second `.set()`
fires the callback again; the callback reads current state, finds nothing
to do, returns.

**Persistence:** `__getstate__` calls `.get()` to extract values.
`__setstate__` calls the setter. `__getcopystate__` same as `__getstate__`.
Each `__getstate__` extends its base's state, which the base's
`__setstate__` reads (`Composite`: parent and children; the owner
mixins: notes, attachments). `fresh_state()` in `domain/base/object.py`
starts a new dict where the base is `object`: its `__getstate__`
(Python 3.11+) returns the live `__dict__`.

---

## Event Batching During Load

When a domain object is loaded from a file, all of its fields are restored
at once. Without batching, each field restoration would fire its own change
notification — dozens of individual events for a single load operation.
Event batching collects all these notifications into one batch that fires
once at the end of the load.

This works through three parts:

1. **`__setstate__` is decorated with `@patterns.eventSource`**, which
   creates a shared `event` object and batches all notifications raised
   during the method.

2. **Setters accept `event=None`** so they can receive the shared
   event from `__setstate__`. This parameter is optional — when called
   from normal code (not during load), `event` defaults to `None` and
   the Attribute creates its own event.

3. **`__setstate__` passes `event=event` to every setter call**, connecting
   each field restoration to the shared batch.

If a setter does not accept `event`, or `__setstate__` does not pass it,
that field's notification falls outside the batch and fires individually.
All setters must follow this convention.

**See:** `taskcoachlib/domain/base/object.py` — `Object.__setstate__()` and
setters (e.g. `setSubject`) for the reference implementation.
`taskcoachlib/patterns/observer.py` — `@eventSource` decorator.

---

## Volatile vs Persisted Attributes

Not all Attributes are persisted. Both use the same `Attribute` class — the
only difference is whether `__getstate__` includes the field.

**Persisted** — included in `__getstate__` / `__setstate__`, loaded from XML.

**Volatile** — NOT in `__getstate__`, recomputed at runtime. Start as `None`,
populated by external computation (e.g. fields derived from other fields,
or recomputed by periodic polling).

Volatile Attributes provide the same equality-check and event-notification
benefits. The equality check is especially valuable for volatile fields that
get recomputed frequently — repeated `.set()` with the same derived value
is a no-op.

---

## Modification Date

**Ruling, 2026-09-27:** any change to an item's stored data sets its
modification date to now, at the moment of the change, however it is
made. The date is logging data, not functional data: it keeps
fractions of a second (`date.Timestamp`, microseconds, also in the
file), so changes within one second stay ordered
([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#time-resolution)).
A new item's modification date starts at its creation date (ruling,
2026-09-28); read from a file without one, the item was not modified
since its creation, and without either date both are unknown. The data layer does it, as part of storing the value: callers
never set it, computed values (status, time spent, budget left,
revenue, styles) do not change it, and loading restores the stored
date without touching it. The interface shows the new date at once,
saved or not. Undo reverts the change and so its dates: every date
the change set goes back to what it was before, including those of
items it changed in turn (a parent completed by its last subtask);
redo puts back the dates from the change
([UNDO_REDO.md](UNDO_REDO.md#modification-dates)). Merging
files keeps the newest copy of each item
([PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)), so it has to be
exact.

How: every stored field is an Attribute or a SetAttribute, and these
set their owner's modification date when their value changes;
Attributes of computed values are marked volatile and do not.

**Ruling, 2026-09-28: a link belongs to the item that points.** A
subitem's parent, an owned note's or attachment's owner, an effort's
task and a task's prerequisites are that item's own data: changing
them sets its date. The reverse lists (children, owned notes and
attachments, efforts, dependencies) are derived and set no date.
Merging follows the same rule
([PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)). Category
membership still sets the date on both sides until its direction is
decided ([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#open-questions-and-issues-found)).

Before step 0 (traced 2026-09-27) only commands set it, on the items
they were given (`BaseCommand.modified_items()`, `command/base.py`),
so these changes left it as it was:

- Changes a command causes on other items: completing the last open
  subtask completes the parent, completing a parent completes its
  subtasks and clears their recurrence, reopening a subtask reopens its
  parent, adding or removing a subtask completes or reopens the parent
  (`task.py`, `_onCompletionDateTimeChanged()`, `addChild()`,
  `removeChild()`); completing a task stops its running effort; a
  prerequisite adds the dependency to the other task
  (`add_prerequisites()`).
- Changes outside commands: the scheduler clearing a completed task's
  reminder (`processReminder()`), snoozing in the reminder dialog
  (`ReminderController`), a Todo.txt import updating an existing task.

Step 0 covers those that change Attributes (completion date, reminder,
effort stop), step 7 the recurrence (cleared on completed subtasks,
and the count recurring advances). The dependency a prerequisite adds
is its reverse, not saved, so it sets no date (9). Subtask links wait
for row 10. Until the last
row, commands still set the date too, on the items they were given.

Migration, one field at a time, simplest first; each becomes an
Attribute whose change sends a Publisher event with the item as source
and sets the modification date, then is tested:

| # | Field | Today | Status |
|---|---|---|---|
| 0 | Attribute and SetAttribute set their owner's modification date; computed (derived, effective) Attributes are volatile | Commands set it | Done |
| 1 | Category style priority | Plain value, Publisher, never saved | Done, saved as `stylePriority` |
| 2 | Category exclusive subcategories | Plain value, Publisher | Done |
| 3 | Task hourly fee, fixed fee | Plain values, pypubsub | Done: Attributes, Publisher (`task.hourlyFee`, `task.fixedFee`) |
| 4 | Task budget | Plain value, pypubsub | Done: Attribute, Publisher (`task.budget`); budget left stays computed |
| 5 | Task "mark completed when all subtasks are" | Plain value, pypubsub | Done: Attribute, Publisher |
| 6 | Task percentage complete, planned duration and its mode | Attributes, pypubsub | Done: Publisher; the duration and mode now mark the file unsaved by their own events |
| 7 | Task recurrence | Plain value, pypubsub | Done: Attribute, Publisher; recurring sets a copy with the next count, instead of changing it in place |
| 8 | Effort start, stop, entry mode, task | Attributes (not the task), pypubsub; the date is not saved | Done: the dates are saved; start, stop, entry mode and task are Publisher events; moving to another task sets the date. Duration, revenue and tracking stay computed messages |
| 9 | Task prerequisites (dependencies are their reverse) | Plain sets, pypubsub | Done: prerequisites a SetAttribute, dependencies derived (no date); Publisher |
| 10 | Links: subtasks and parent, owned notes and attachments, efforts | Plain lists, Publisher | Done: the pointing item's date (ruling above); merging takes owned items item by item |
| 11 | View state: a category's filter state, the expanded state | Plain values | To decide: stored, but not the item's data |
| 12 | Commands no longer set the date: the undo log records every change ([UNDO_REDO.md](UNDO_REDO.md#todo-one-undo-log)) | | Last |

---

## Three-Layer Relationship

Change detection operates at three layers. Each has its own mechanism,
but they share the same principle: don't process if nothing changed.

**Layer 1: Attribute (Domain)** — `Attribute.set()` equality check on a
single field of a single domain object. Self-limiting: repeated `.set()`
with the same value only fires an event on the first actual change.
**File:** `taskcoachlib/domain/base/attribute.py`

**Layer 2: AttributeSync (UI↔Domain)** — Bidirectional sync between a UI
control and a domain object. User edits control → executes command → domain
updated. Domain changes → `control.SetValue()` → UI updated. Expects
controls to implement `GetValue()`/`SetValue()`. Standard pattern:
`EVT_VALUE_CHANGED` with immediate commit — the control decides when to fire
(on blur for user edits, immediately for programmatic writes). Composite
controls like `DateTimeComboCtrl` inherit `wx.EvtHandler` and own the event,
firing on sub-control blur and state transitions. Legacy sites still use
`EVT_KILL_FOCUS` (see [TODO #1](#todo)).
**File:** `taskcoachlib/gui/dialog/attributesync.py`
**Usage:** See DATETIME_CONTROLS.md, MONETARY_CONTROLS.md

**Layer 3: Change-Only Rule (Widget↔Widget)** — Manual equality checks +
source_field guards + quiet flags in UI sync functions
(`__syncTaskState`, `__sync_effort_state`). The UI-level equivalent of
`Attribute.set()`'s equality check, applied to widget-to-widget
synchronization. Documented in DURATION_CALCULATIONS.md section 0.2.

### Layer 2 Requirement

Every persisted Attribute field shown in an editor needs a corresponding
signal subscription to handle external domain changes. This is either:

- **AttributeSync** — for fields with a control that supports
  GetValue/SetValue and a corresponding edit command.
- **Manual signal subscription** — for fields with custom controls
  (dropdowns, checkboxes) where AttributeSync doesn't fit directly.
  Currently a mix of `registerObserver` (legacy) and `pub.subscribe`
  (pypubsub) — see [PUBLISHER_OBSERVER.md — Signal Dispatch](PUBLISHER_OBSERVER.md#signal-dispatch)
  for target architecture.

Without Layer 2, the Attribute pattern is incomplete: the domain notifies
correctly, but no UI listens.

Layer 2 handlers that call Layer 3 sync methods (e.g. `__syncTaskState`)
must pass `source_field` so the sync logic knows which field changed
(DURATION_CALCULATIONS.md section 0.1) and skips steps that would
overwrite the user's change.

See also: [LOCALE.md](LOCALE.md) for how locale settings interact with
Layer 2 controls (decimal separator, date/time format detection).
[NUMERIC_CONTROLS.md](NUMERIC_CONTROLS.md) and
[MONETARY_CONTROLS.md](MONETARY_CONTROLS.md) for `EVT_VALUE_CHANGED`
migration of monetary controls (TODO #1).

