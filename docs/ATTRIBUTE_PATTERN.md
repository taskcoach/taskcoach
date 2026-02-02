# Attribute Pattern

The domain model's change-detection and event-notification pattern.

## Index

- [TODO](#todo)
- [Overview](#overview)
- [Attribute Class API](#attribute-class-api)
- [SetAttribute Class API](#setattribute-class-api)
- [Value Normalization](#value-normalization)
- [Setter / Callback Pattern](#setter--callback-pattern)
- [Event Batching During Load](#event-batching-during-load)
- [Volatile vs Persisted Attributes](#volatile-vs-persisted-attributes)
- [Three-Layer Relationship](#three-layer-relationship)

---

## TODO

1. **Migrate remaining `EVT_KILL_FOCUS` AttributeSync sites to
   `EVT_VALUE_CHANGED`.** The legacy pattern binds AttributeSync to
   `EVT_KILL_FOCUS` (blur). This works for user edits (commit on focus
   loss), but is invisible to programmatic writes — widget methods like
   `SetDuration()` fire `EVT_VALUE_CHANGED`, not `EVT_KILL_FOCUS`, so
   the AttributeSync never sees them and the domain is never updated.
   **Done:** DurationCtrl (task and effort) and all DateTimeCombo fields
   now use plain `EVT_VALUE_CHANGED` with immediate commit — no
   `commit_on_focus_loss` needed because `FieldsCtrl` fires only on
   blur (user) or `SetDuration()` (programmatic). See TODO #2.
   **Remaining:** monetary controls (budget, hourly fee, fixed fee) are
   FieldsCtrl-based and should follow the same pattern. Subject,
   description, and attachment location use `wx.TextCtrl` (fires
   per-keystroke `EVT_TEXT`) — different migration path. See
   [Three-Layer Relationship](#three-layer-relationship), Layer 2.

2. **Remove `commit_on_focus_loss` from AttributeSync.** The
   `commit_on_focus_loss` mechanism was added to batch per-keystroke
   `EVT_VALUE_CHANGED` events into a single command on blur. This is
   the wrong separation of concerns — whether events fire per-keystroke
   or on blur is the **control's** responsibility, not the sync layer's.
   `FieldsCtrl` now handles this correctly: `NumericField.SetValue()`
   no longer fires `NotifyValueChanged()`; instead, `FieldsCtrl` fires
   `EVT_VALUE_CHANGED` only on `_onKillFocus` (user finished typing)
   and from `SetDuration()`/`SetTime()`/`SetDate()` (programmatic
   complete-value writes). Every `EVT_VALUE_CHANGED` that reaches
   `AttributeSync` represents a final value — immediate commit is
   always correct. The `commit_on_focus_loss` parameter, the
   `__editSessionValue`/`__hasChanges` tracking, the `__onSetFocus`/
   `__onKillFocus` handlers, and the `commit()` method can all be
   removed. All `AttributeSync` sites should use plain
   `EVT_VALUE_CHANGED` with immediate commit (the default).
   **Status:** `commit_on_focus_loss` has zero callers (the only caller,
   `addDateEntry`, was dead code and has been deleted). The mechanism in
   `attributesync.py` can be removed now.

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
or sentinel values to `None` at the boundary (constructor, setter entry,
XML load). This guarantees `None == None` for the equality check.

| Raw Value | Normalized | Rationale |
|-----------|-----------|-----------|
| `TimeDelta()` (zero duration) | `None` | "no duration set" |
| `date.DateTime()` (maxDateTime sentinel) | `None` | "no date set" |
| Missing from XML / state dict | `None` | Field not present |
| `""` or invalid value for mode/enum fields | `None` | "no mode set" — not a silent fallback |

Without normalization, the same logical state ("not set") can have multiple
representations (zero, sentinel, None, empty string). The Attribute equality
check only works reliably when the same logical state always has the same value.

Normalization happens in the **setter**, before calling `.set()`.
Example: `setPlannedDurationMode()` maps old mode names and rejects
invalid values to `None` before delegating to the Attribute.

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

**Notification callback** — fires `pub.sendMessage`, `markDirty`,
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
controls like `DateTimeCombo` inherit `wx.EvtHandler` and own the event,
firing on sub-control blur and state transitions. Legacy sites still use
`EVT_KILL_FOCUS` (see [TODO #1](#todo)).
**File:** `taskcoachlib/gui/dialog/attributesync.py`
**Usage:** See DATETIME_CONTROLS.md, MONETARY_CONTROLS.md

**Layer 3: Change-Only Rule (Widget↔Widget)** — Manual equality checks +
source_field guards + quiet flags in UI sync functions
(`__syncTaskState`, `__syncEffortState`). The UI-level equivalent of
`Attribute.set()`'s equality check, applied to widget-to-widget
synchronization. Documented in DURATION_CALCULATIONS.md section 0.2.

### Layer 2 Requirement

Every persisted Attribute field shown in an editor needs a corresponding
pubsub subscription to handle external domain changes. This is either:

- **AttributeSync** — for fields with a control that supports
  GetValue/SetValue and a corresponding edit command.
- **Manual pub.subscribe** — for fields with custom controls (dropdowns,
  checkboxes) where AttributeSync doesn't fit directly.

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

