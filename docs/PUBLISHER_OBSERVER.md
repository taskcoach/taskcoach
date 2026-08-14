# Publisher / Observer Signal Dispatch

Signal dispatch architecture, pypubsub migration, and signaling lifecycle
cleanup for the Task Coach domain model.

See [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md) for the Attribute pattern
itself (setter/callback, equality check, event batching, three-layer
relationship) — signal dispatch exists to serve Attribute change notification.

## Index

- [TODO](#todo)
- [Signal Dispatch](#signal-dispatch)
  - [Case Study: Tree Mode Toggle](#case-study-tree-mode-toggle)
- [Signaling System Cleanup](#signaling-system-cleanup)
- [Migration Log](#migration-log)
- [Active pypubsub Settings Listeners](#active-pypubsub-settings-listeners)

---

## TODO

1. **Migrate signal dispatch to per-instance.** Some Attribute callbacks
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
   `categoryfiltermatchall` migrated from pubsub to Publisher — both
   `CategoryFilter` and `CategoryViewerFilterChoice` now subscribe via
   `registerObserver` on the settings instance.
   `view.statusbar` and `view.toolbar` migrated from pubsub to Publisher —
   `MainWindow` now subscribes via `registerObserver` on the settings
   instance (added `patterns.Observer` to MRO).
   `view.autoscrollselection` (auto-scroll toggle) uses Publisher
   dispatch from the start: `ToggleAutoScroll` (toolbar button sync)
   and `Viewer.on_auto_scroll_changed` (re-center on enable) both
   subscribe via `registerObserver` on the settings instance.
   **Remaining:** Task dates, percentage, duration; Effort fields.

2. **Modularize and clean up the signaling system.** The three independent
   cleanup mechanisms (wx C++ destruction, `removeInstance()`, Python GC)
   don't coordinate, causing zombie callbacks and 20+ silent `try/except`
   guards. Target: a single automatic cleanup mechanism where destroying
   an object removes all its subscriptions. See
   [Signaling System Cleanup](#signaling-system-cleanup)
   for the full plan and current band-aids.
   **Done:** `MethodProxy` (strong references) replaced with
   `WeakMethodProxy` (`weakref.WeakMethod`). Publisher no longer prevents
   GC of destroyed wx widgets. Dead subscribers are detected and pruned
   automatically during `notifyObservers()` dispatch.
   **Remaining:** Hook `EVT_WINDOW_DESTROY` → `removeInstance()` for
   immediate cleanup (currently relies on GC timing). Remove DEAD-OBJ
   guards once cleanup is proven reliable.

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
Menu Radio Option ── do_command(event) ──────────────┤
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
                                    set_choice(from settings) EnableTool(id, cmd.enabled())
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

## Signaling System Cleanup

### Problem

The signaling/event system is fragmented across three independent mechanisms
that don't coordinate lifecycle cleanup:

1. **wx C++ destruction** — `Destroy()` frees the C++ widget tree. Python
   wrappers become zombies (accessing them segfaults).
2. **patterns.Observer.removeInstance()** — Removes pubsub + Publisher
   subscriptions for a Python object. Must be called explicitly.
3. **Python garbage collection** — Frees Python objects when refcount hits
   zero. Triggers `__del__`.

None of these know about each other. When wx destroys a widget, it doesn't
call `removeInstance()`. When `removeInstance()` runs, it doesn't know if
the wx widget is already dead. The result is 20+ `try/except RuntimeError:
pass` guards scattered across the codebase — band-aids over missing lifecycle
coordination.

### Goal

A single, automatic cleanup mechanism: when an object goes away, all its
subscriptions (pubsub, Publisher, wx events) are automatically removed.
No manual unsubscribe, no silent `except` guards, no zombie callbacks.

### Current band-aids (February 2026)

- `UICommand` was changed to inherit from `patterns.Observer` so
  `removeInstance()` cleans up all subscription types automatically.
- `toolbar.Clear()` and `menu.clearMenu()` call `removeInstance()` during
  teardown.
- `Editor.on_close_editor()` explicitly cleans up its UICommands.
- 20+ `try/except RuntimeError: pass` blocks now log with `prefix="DEAD-OBJ"`
  so zombie access is visible. These should eventually be eliminated, not
  just logged.

### Target architecture

1. **Unify on one signal system.** Migrate all pypubsub usage to Publisher
   signaling (per-instance dispatch). Then migrate Publisher to a modern
   signal library (Blinker or psygnal) with true per-instance signals.

2. **Automatic cleanup via EVT_WINDOW_DESTROY.** Hook into wx's
   `EVT_WINDOW_DESTROY` event to call `removeInstance()` automatically when
   a window is destroyed. This eliminates the need for manual cleanup in
   every close handler.

3. **Remove all DEAD-OBJ guards.** Once cleanup is automatic, the
   `try/except RuntimeError` guards become dead code. Remove them.

### Files involved

| Area | Key files |
|------|-----------|
| Observer/Publisher | `taskcoachlib/patterns/observer.py` |
| UICommand lifecycle | `taskcoachlib/gui/uicommand/base_uicommand.py` |
| Toolbar cleanup | `taskcoachlib/gui/toolbar.py` |
| Menu cleanup | `taskcoachlib/gui/menu.py` |
| Editor cleanup | `taskcoachlib/gui/dialog/editor.py` |
| Viewer cleanup | `taskcoachlib/gui/viewer/base.py` |

**Status:** Planned — incremental. Band-aids in place, root cause understood.

---

## Migration Log

| Signal | Action | Location |
|--------|--------|----------|
| `view.categoryfiltermatchall` | Migrated to Publisher | `taskcoachlib/gui/viewer/category/filter.py` |
| `view.statusbar` | Migrated to Publisher | `taskcoachlib/gui/mainwindow.py` |
| `view.toolbar` | Migrated to Publisher | `taskcoachlib/gui/mainwindow.py` |
| `view.weekstartmonday` | Deleted (dead — topic name mismatch) | `taskcoachlib/gui/viewer/task.py` |
| `view.efforthourstart` | Deleted (no live-update needed) | `taskcoachlib/gui/viewer/task.py` |
| `view.efforthourend` | Deleted (no live-update needed) | `taskcoachlib/gui/viewer/task.py` |
| `file.recentfiles` | Migrated to Publisher | `taskcoachlib/gui/menu.py` |
| `commandhistory.changed` | Migrated to Publisher | `taskcoachlib/gui/uicommand/uicommand.py` |
| `feature.task_duration_presets` | Migrated to Publisher | `taskcoachlib/gui/dialog/editor.py` (DatesPage) |
| `feature.effort_duration_presets` | Migrated to Publisher | `taskcoachlib/gui/dialog/editor.py` (EffortEditBook) |

---

## GTK3 Dynamic Menu Item Sizing

Menus with dynamic items (recent files, undo/redo labels) must be populated
at init time and updated via Publisher events when the underlying data
changes — **never during `EVT_MENU_OPEN`**.

GTK3 does not recalculate menu popup geometry when items are modified inside
an `EVT_MENU_OPEN` handler. This manifests in two ways:

1. **Scroll arrows on first open.** Adding/removing items during
   `EVT_MENU_OPEN` changes the item count after GTK has already sized the
   popup. Scroll arrows appear even with plenty of screen space. Second
   open sizes correctly because GTK caches the updated count.
2. **Menu too narrow for new label text.** `SetItemLabel()` during
   `EVT_MENU_OPEN` changes label width but GTK does not widen the popup.
   Text is clipped on first open; second open recalculates. This affects
   EditUndo/EditRedo and EditPasteAsSubItem (see [MENUS.md TODO #2](MENUS.md#todo)).

**Pattern:** populate the menu at construction, then subscribe to a
Publisher event that fires when the underlying data changes. The handler
updates items while the menu is closed, so GTK always sees the correct
geometry at popup time.

**Affected menus:**
- **FileMenu** — recent files list. Subscribes to `file.recentfiles`
  Publisher event on the settings object. **Fixed** (December 2025).
- **EditMenu** — undo/redo labels were updated via `current_menu_text()`
  during `EVT_MENU_OPEN`. **Fixed** — `CommandHistory` now fires a Publisher
  event; `EditUndo`/`EditRedo` subscribe and call `update_menu_text()`
  proactively. `current_menu_text()` returns `None` to skip `SetItemLabel`
  during popup.

**References:**
- [PYTHON3_MIGRATION_3.md — GTK3 Menu Size Allocation Bug](PYTHON3_MIGRATION_3.md#gtk3-menu-size-allocation-bug)
  for the full root cause analysis, timeline, and testing checklist.
- GNOME GTK Issue #473
- `taskcoachlib/gui/menu.py` — `FileMenu` class docstring

---

## Active pypubsub Settings Listeners

Settings topics that still have pypubsub subscribers. This is the tracking
list for the migration — entries are removed as they are migrated or deleted.

| Topic pattern | Subscriber location |
|---------------|---------------------|
| `settings.icon` / `settings.icon_dark` | `taskcoachlib/domain/task/task.py:128-131` |
| `settings.fgcolor` / `settings.fgcolor_dark` | `taskcoachlib/domain/task/task.py:116,119` |
| `settings.bgcolor` / `settings.bgcolor_dark` | `taskcoachlib/domain/task/task.py:122,125` |
| `settings.behavior.duesoonhours` | `taskcoachlib/domain/task/task.py:133` |
| `settings.window.theme` | `taskcoachlib/domain/task/task.py:132`, `taskcoachlib/gui/viewer/task.py:160` |

---

**Last Updated:** March 2026
