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
- [Setter / Callback Pattern](#setter--callback-pattern)
- [Event Batching During Load](#event-batching-during-load)
- [Volatile vs Persisted Attributes](#volatile-vs-persisted-attributes)
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

2. **Migrate signal dispatch to per-instance.** Some Attribute callbacks
   (Task dates, percentage, duration; Effort fields) use pypubsub
   (`pub.sendMessage`) which is topic-based broadcast — every subscriber
   receives every object's changes. This is wrong for per-instance
   Attribute signals. These fields should be migrated back to per-instance
   dispatch (legacy `registerObserver` with `eventSource`, or a future
   modern signal library). See [Signal Dispatch](#signal-dispatch).
   **Done:** Task priority, Attachment location, and all 16
   derived/effective appearance event types migrated to per-instance
   dispatch (dropped `"pubsub."` prefix). Tree mode toggle migrated
   from pubsub to Publisher signaling (see
   [Case Study: Tree Mode Toggle](#case-study-tree-mode-toggle)).
   **Remaining:** Task dates, percentage, duration; Effort fields.

---

## Signal Dispatch

Attribute change notifications must be **per-instance** — "this specific
object's field changed" — not broadcast. An Attribute is always a field on
a specific domain object. Subscribers (editors, viewers, sync handlers) care
about specific objects, not all objects of a type.

### Requirement: per-instance signals

All Attribute callbacks must use **per-instance signal dispatch**: the
subscriber connects to a specific sender, and the dispatch layer delivers
only to subscribers of that sender. No subscriber should receive
notifications from objects it did not subscribe to.

This rules out topic-based broadcast systems (like pypubsub's
`pub.sendMessage`) where every subscriber to a topic receives every
notification regardless of sender, requiring handler-side filtering.

### Current state (mixed, partially incorrect)

The codebase has two signal dispatch systems:

**Legacy Publisher** (`patterns.Publisher`, `registerObserver`/
`notifyObservers`) — sender-filtered dispatch via a global routing table.
Subscriber registers for a `(eventType, eventSource)` pair; dispatch does
a dict lookup on that key and delivers only to matching observers.
Observers registered for other senders are never touched — O(1) lookup,
not iteration over all observers. Used by the base `Object` fields
(subject, description, appearance, derived/effective) and collection fields
(categories, categorizables).

Note: the Publisher is a **Singleton** (one global registry), not true
per-instance signals (where the signal object lives on the instance itself,
e.g. `task.icon_changed.connect(handler)`). The difference is structural —
a global routing table vs per-instance subscriber lists — not behavioral.
The dispatch semantics are per-instance: only matching subscribers are
invoked, no subscriber has to check "is this message for me?"

**pypubsub** (`pub.sendMessage`/`pub.subscribe`) — topic-based broadcast.
All subscribers to a topic receive all messages regardless of sender. No
per-sender filtering at dispatch; subscribers must check the `sender` kwarg
in the handler to decide whether to act. Used by some Task fields (dates,
percentage, duration) and Effort fields that were migrated circa 2012.
The migration was intended to replace the legacy system entirely but
stalled partway.

The pypubsub migration was motivated by API simplicity and weak reference
support, but it introduced broadcast dispatch for what are inherently
per-instance signals. This is architecturally wrong: an editor showing one
task receives (and discards) notifications from every other task in the
system.

### Target architecture

1. **Immediate:** new Attribute fields use the legacy Publisher with
   sender-filtered `eventSource` dispatch. Dispatch semantics are correct
   (only matching subscribers called), even though the implementation is a
   global routing table rather than true per-instance signal objects.

2. **Future:** migrate all signal dispatch to a modern signal library
   following the Qt signals/slots pattern (e.g. Blinker or psygnal). These
   use true per-instance signals — the signal object lives on the instance
   (`task.icon_changed.connect(handler)`), no global registry. This would
   replace both the legacy Publisher and pypubsub with a single system that
   supports per-sender subscription natively, weak references, and a clean
   API.

3. **Revert pypubsub fields:** the Task and Effort fields currently using
   `pub.sendMessage` should be migrated back to sender-filtered dispatch
   (either legacy Publisher or the future signal library). pypubsub should
   be removed as a dependency once all fields are migrated.

### Naming convention

Event type strings prefixed `"pubsub."` were introduced during the
pypubsub migration. The viewer's `__startObserving()` in `base.py` uses
this prefix to choose dispatch system: `"pubsub."` → `pub.subscribe`,
otherwise → `registerObserver`.

New event types should **not** use the `"pubsub."` prefix. They should use
the legacy Publisher dispatch (per-instance) until the future signal library
migration.

### Case Study: Tree Mode Toggle

The tree/list mode toggle (task viewer) was migrated from pubsub to
Publisher signaling. This is the reference example for migrating UI-level
pubsub subscriptions to per-instance dispatch.

**Before (pubsub — broadcast):**

```
dropdown/menu
  → settings.setboolean("treemode")
    → pub.sendMessage("settings.taskviewer.treemode")
      → TaskViewer.onTreeListModeChanged  (subscriber 1)
      → TaskViewerTreeOrListChoice.on_setting_changed  (subscriber 2)
```

Two independent pubsub subscribers, both keyed on the same global topic
string. Any code writing `settings.setboolean("treemode")` triggers both.
No per-instance filtering — a second task viewer's dropdown would also fire.

**After (Publisher — per-instance):**

All three entry points converge on the viewer:

```
Toolbar Dropdown ─── doChoice(choice) ──────────────┐
Menu Radio Option ── doCommand(event) ──────────────┤
                                                     ▼
                                            viewer.set_tree_mode(value)
                                                     │
                                    ┌────────────────┼────────────────┐
                                    ▼                ▼                ▼
                            settings.setboolean  presentation    patterns.Event
                            (persistence only)   .set_tree_mode()   .send()
                                                                     │
                                              ┌──────────────────────┤
                                              ▼                      ▼
                                    Dropdown syncs:          Buttons sync:
                                    setChoice(from settings) EnableTool(id, cmd.enabled())
                                    (_on_view_settings_changed) (_ViewSettingsSync)
```

**Design principles demonstrated:**

1. **Viewer as single authority.** All entry points (toolbar dropdown, menu
   radio) call `viewer.set_tree_mode(value)`. The viewer owns the setting
   write, presentation update, and event dispatch. No caller writes settings
   directly.

2. **Per-instance event type.** The event type is `"viewer%s.view_settings" %
   id(self)`, unique per viewer instance. Two task viewers have separate
   event types — toggling one doesn't affect the other.

3. **Generalized signal.** `view_settings_changed_event_type()` is shared
   across all viewer setting changes (tree mode, aggregation, sort order,
   etc.). The event carries no data — receivers read current state from the
   viewer or settings. `selection_changed_event_type()` remains separate
   because selection change is universal across all viewer types.

4. **Subscribers use `registerObserver` with `eventSource`.** The dropdown
   and button sync objects register for the specific viewer's event:
   ```python
   viewer.registerObserver(
       self._on_view_settings_changed,
       eventType=viewer.view_settings_changed_event_type(),
       eventSource=viewer,
   )
   ```

5. **Automatic cleanup.** `registerObserver()` (from `patterns.Observer`)
   tracks all registered observers. When the viewer is destroyed,
   `removeInstance()` unregisters them. No manual unsubscribe needed.

6. **Settings write is inert.** `settings.setboolean()` still fires a
   pubsub message (`"settings.taskviewer.treemode"`), but nobody subscribes
   to it. The broadcast is harmless — all subscribers use the Publisher
   event instead.

**Files:**
- `taskcoachlib/gui/viewer/task.py` — `TaskViewer.set_tree_mode()`
- `taskcoachlib/gui/uicommand/uicommand.py` — `TaskViewerTreeOrListChoice`,
  `TaskViewerTreeOrListOption`, `_ViewSettingsSync`
- `taskcoachlib/gui/viewer/base.py` — `view_settings_changed_event_type()`

See also: [LIST_MANAGEMENT.md — Scroll After Rebuild](LIST_MANAGEMENT.md#scroll-after-rebuild-tree-views)
for the scroll behavior during mode switch.

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

**Notification callback** — fires change signal (see
[Signal Dispatch](#signal-dispatch)), `markDirty`,
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
controls like `DateTimeComboCtrl` inherit `wx.EvtHandler` and own the event,
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
signal subscription to handle external domain changes. This is either:

- **AttributeSync** — for fields with a control that supports
  GetValue/SetValue and a corresponding edit command.
- **Manual signal subscription** — for fields with custom controls
  (dropdowns, checkboxes) where AttributeSync doesn't fit directly.
  Currently a mix of `registerObserver` (legacy) and `pub.subscribe`
  (pypubsub) — see [Signal Dispatch](#signal-dispatch) for target
  architecture.

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

