# Publisher / Observer Signal Dispatch

Signal dispatch architecture, the move off pypubsub (done 2026-09-28),
and signaling lifecycle cleanup for the Task Coach domain model.

See [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md) for the Attribute pattern
itself (setter/callback, equality check, event batching, three-layer
relationship) — signal dispatch exists to serve Attribute change notification.

## Index

- [TODO](#todo)
- [Signal Dispatch](#signal-dispatch)
  - [Case Study: Tree Mode Toggle](#case-study-tree-mode-toggle)
- [Signaling System Cleanup](#signaling-system-cleanup)
- [Migration Log](#migration-log)
- [Settings Events](#settings-events)

---

## TODO

1. **Done: migrate signal dispatch to per-instance.** Some Attribute callbacks
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
   Task planned start, due, actual start, completion and reminder
   migrated to Publisher (the reminder made an `Attribute`), for the
   master timer list ([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#what-changes-the-master-timer-list)).
   Task hourly and fixed fee, budget, "mark completed when all
   subtasks are", percentage complete, planned duration and its mode
   migrated with the modification date
   ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)).
   Task recurrence, prerequisites and dependencies, and effort start,
   stop, entry mode and task migrated the same way.
   The domain's other messages (computed values too), then the task
   file's, settings', commands' and viewers' messages followed
   (2026-09-28, Migration Log), and pypubsub is no longer a
   dependency: every signal is a Publisher event.

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
   Editor pages (`Page`, `ScrolledPage` in `gui/dialog/editor.py`) call
   `removeInstance()` on their own `EVT_WINDOW_DESTROY`, so their
   subscriptions are removed however the page is destroyed (close
   handler, parent destroy, app exit). A subscriber that raises during
   dispatch is logged with its traceback (`[OBSERVER]`). It is removed
   only if its wx object was deleted, or its own code touched a deleted
   wx object ("has been deleted"); a failure inside a listener it
   called does not count. Otherwise it is kept, so one failure cannot
   silently stop a subscriber such as the per-second `MasterScheduler`.
   A failure that repeats on every event logs its traceback once, then
   a count every 100 repeats.
   **Done 2026-09-28:** every subscription ends with its owner
   ([Signaling System Cleanup](#signaling-system-cleanup)), and the
   guards that became unreachable are removed.

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

### Current state

The codebase has one signal dispatch system, the Publisher; pypubsub was
removed 2026-09-28.

**Publisher** (`patterns.Publisher`, `registerObserver`/
`notifyObservers`) — sender-filtered dispatch via a global routing table.
Subscriber registers for a `(eventType, eventSource)` pair; dispatch does
a dict lookup on that key and delivers only to matching observers.
Observers registered for other senders are never touched — O(1) lookup,
not iteration over all observers. Every signal uses it: domain fields,
collections, the task file, settings, commands and viewers.

Note: the Publisher is a **Singleton** (one global registry), not true
per-instance signals (where the signal object lives on the instance itself,
e.g. `task.icon_changed.connect(handler)`). The difference is structural —
a global routing table vs per-instance subscriber lists — not behavioral.
The dispatch semantics are per-instance: only matching subscribers are
invoked, no subscriber has to check "is this message for me?"

**pypubsub** (removed; `pub.sendMessage`/`pub.subscribe`): topic-based broadcast.
All subscribers to a topic receive all messages regardless of sender. No
per-sender filtering at dispatch; subscribers must check the `sender` kwarg
in the handler to decide whether to act. Task and Effort fields were
migrated to it circa 2012; the migration was intended to replace the
legacy system entirely but stalled partway. Since 2026-09-28 nothing
uses it and it is no longer a dependency (see [TODO](#todo)).

The pypubsub migration was motivated by API simplicity and weak reference
support, but it introduced broadcast dispatch for what are inherently
per-instance signals. This was architecturally wrong: an editor showing one
task received (and discarded) notifications from every other task in the
system.

### Target architecture

1. **Immediate:** new Attribute fields use the Publisher with
   sender-filtered `eventSource` dispatch. Dispatch semantics are correct
   (only matching subscribers called), even though the implementation is a
   global routing table rather than true per-instance signal objects.

2. **Future:** migrate all signal dispatch to a modern signal library
   following the Qt signals/slots pattern (e.g. Blinker or psygnal). These
   use true per-instance signals — the signal object lives on the instance
   (`task.icon_changed.connect(handler)`), no global registry. This would
   replace the Publisher with a system that supports per-sender
   subscription natively, weak references, and a clean API.

3. **Done 2026-09-28: revert pypubsub fields.** Every message moved to
   the Publisher and pypubsub was removed as a dependency.

### Naming convention

Event type strings prefixed `"pubsub."` were introduced during the
pypubsub migration, and listeners chose the dispatch system by that
prefix. Since 2026-09-28 every event type is a Publisher event and none
has the prefix. New event types use the Publisher (per-instance) until
the future signal library migration.

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

6. **Settings write.** `settings.setboolean()` sends the settings
   event `taskviewer.treemode`, the settings as source
   ([Settings Events](#settings-events)); the toggle's subscribers listen
   to the viewer's own event instead.

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
2. **patterns.Observer.removeInstance()**: removes the Publisher
   subscriptions of a Python object. Must be called explicitly.
3. **Python garbage collection** — Frees Python objects when refcount hits
   zero. Triggers `__del__`.

None of these know about each other. When wx destroys a widget, it doesn't
call `removeInstance()`. When `removeInstance()` runs, it doesn't know if
the wx widget is already dead. The result is 20+ `try/except RuntimeError:
pass` guards scattered across the codebase — band-aids over missing lifecycle
coordination.

### Goal

A single, automatic cleanup mechanism: when an object goes away, all its
subscriptions (Publisher, wx events) are automatically removed.
No manual unsubscribe, no silent `except` guards, no zombie callbacks.

### Current band-aids (February 2026)

- `UICommand` was changed to inherit from `patterns.Observer` so
  `removeInstance()` cleans up all subscription types automatically.
- `toolbar.Clear()` and `menu.clearMenu()` call `removeInstance()` during
  teardown.
- `Editor.on_close_editor()` explicitly cleans up its UICommands.
- The `try/except RuntimeError: pass` blocks log with `prefix="DEAD-OBJ"`
  so zombie access is visible; those left guard what unsubscribing
  cannot (item 3 below).

### Target architecture

1. **Unify on one signal system.** Done 2026-09-28 for pypubsub: every
   signal is a Publisher event. Next: migrate the Publisher to a modern
   signal library (Blinker or psygnal) with true per-instance signals.

2. **Automatic cleanup via EVT_WINDOW_DESTROY.** Done 2026-09-28:
   - A window's subscriptions, through the `Observer` mixin or the
     `Publisher` directly, end when it is destroyed: the Publisher
     binds `EVT_WINDOW_DESTROY` at its first subscription
     (`Publisher.remove_observers_of()`). A window must subscribe after
     its wx `__init__`.
   - A toolbar's commands unsubscribe when the toolbar is destroyed
     (rebuilding the main toolbar destroys it without `Clear()`).
   - A destroyed submenu or popup menu drops its subscriptions
     (`Menu.DestroyItem()`, `Menu.Destroy()`).
   - An editor page ends its field syncs' (`AttributeSync`) with its
     own: they are not windows, and some entries wrap several widgets.

3. **Remove the DEAD-OBJ guards.** Done 2026-09-28 where unreachable: a
   liveness check just before the call (`if not self`, `if
   self.toolbar`), or an owner that now unsubscribes. The others stay;
   they guard what unsubscribing cannot:

   | Guarded against | Where |
   |---|---|
   | A delayed call reaching a window closed meanwhile | `patterns.later` skips it when its owner is gone ([DEFERRED_CALLS.md](DEFERRED_CALLS.md)); the older `__safe*()` wrappers in the widgets and viewers, the in-place editors, `Editor._deferred_destroy()`, and the viewer container's focus remain as a second check; the `not self or IsBeingDeleted()` checks also skip a window being deleted, which the service still runs |
   | wx events while a window's children are being destroyed | `TaskEntry._onDestroy()`, `Viewer.SetFocus()`, `AttributeSync`'s callback, the tree and list `curselection()`, the column sort |
   | Menu items that outlive their menu, wx assertions | `update_menu_text()`, `MenuItem.update_state()`, `on_update_menu()` |
   | Shutdown | `Application.display_message()` |

   The app-wide `wx.CallAfter` guard (`workarounds/monkeypatches.py`)
   covers library code's delayed calls to a deleted window's own
   methods.

### Files involved

| Area | Key files |
|------|-----------|
| Observer/Publisher | `taskcoachlib/patterns/observer.py` |
| UICommand lifecycle | `taskcoachlib/gui/uicommand/base_uicommand.py` |
| Toolbar cleanup | `taskcoachlib/gui/toolbar.py` |
| Menu cleanup | `taskcoachlib/gui/menu.py` |
| Editor cleanup | `taskcoachlib/gui/dialog/editor.py` |
| Viewer cleanup | `taskcoachlib/gui/viewer/base.py` |

**Status:** Done 2026-09-28, but for the signal library (1).

---

## Migration Log

| Signal | Action | Location |
|--------|--------|----------|
| `view.categoryfiltermatchall` | Migrated to Publisher | `taskcoachlib/domain/category/filter.py` (CategoryFilter), `taskcoachlib/gui/uicommand/uicommand.py` (CategoryViewerFilterChoice) |
| `view.statusbar` | Migrated to Publisher | `taskcoachlib/gui/mainwindow.py` |
| `view.toolbar` | Migrated to Publisher | `taskcoachlib/gui/mainwindow.py` |
| `view.weekstartmonday` | Deleted (dead — topic name mismatch) | `taskcoachlib/gui/viewer/task.py` |
| `view.weekstart`, `calendarviewer.gradient` | Added 2026-09-28: the calendar viewer applies them at once | `taskcoachlib/gui/viewer/task.py` |
| `view.efforthourstart` | Deleted (no live-update needed) | `taskcoachlib/gui/viewer/task.py` |
| `view.efforthourend` | Deleted (no live-update needed) | `taskcoachlib/gui/viewer/task.py` |
| `file.recentfiles` | Migrated to Publisher | `taskcoachlib/gui/menu.py` |
| `commandhistory.changed` | Migrated to Publisher | `taskcoachlib/gui/uicommand/uicommand.py` |
| `settings.statussortpriority.changed` | Migrated to Publisher | `taskcoachlib/gui/dialog/preferences.py` (StatusesPage), `taskcoachlib/domain/task/sorter.py` (Sorter) |
| `templates.saved` | Deleted (menus refill when shown) | `taskcoachlib/gui/menu.py` (TaskTemplateMenu) |
| `effortviewer.aggregation` | Deleted (menu refills before popup) | `taskcoachlib/gui/menu.py` (EffortViewerColumnPopupMenu) |
| `spellcheck.colours.changed` | Migrated to Publisher | `taskcoachlib/gui/dialog/preferences.py` (ThemePage), `taskcoachlib/widgets/textctrl.py` (_StyledTextCtrl) |
| `calendar.colours.changed` | Migrated to Publisher | `taskcoachlib/gui/dialog/preferences.py` (ThemePage), `taskcoachlib/gui/viewer/task.py` (CalendarViewer), `taskcoachlib/widgets/maskedtimectrl.py` (_CalendarComboPopup) |
| `powermgt.on` / `powermgt.off` | Migrated to Publisher | `taskcoachlib/gui/mainwindow.py` (MainWindow), `taskcoachlib/gui/idlecontroller.py` (IdleController), `taskcoachlib/gui/viewer/task.py` (BaseTaskViewer, `powermgt.on` only) |
| `pubsub.task.plannedStartDateTime`, `dueDateTime`, `actualStartDateTime`, `completionDateTime` | Migrated to Publisher as `task.<field>`, the task and each ancestor as sources | `taskcoachlib/domain/task/task.py` (Task), `taskcoachlib/domain/task/sorter.py` (Sorter), `taskcoachlib/gui/taskbaricon.py`, `taskcoachlib/gui/dialog/reminder.py` (ReminderDialog); the others route by prefix |
| `pubsub.task.reminder` | Migrated to Publisher as `task.reminder`; the reminder is an `Attribute`, so snoozing also notifies the ancestors | `taskcoachlib/domain/task/task.py` (Task) |
| `pubsub.task.status`, `efforts`, `track`, `timeSpent`, `budgetLeft`, `revenue`; `pubsub.effort.track`, `duration`, `revenue`; `pubsub.<class>.expandedContexts`; `pubsub.<sorter>.sorted`; `pubsub.effort.composite.empty` | Migrated to Publisher without the `pubsub.` prefix; a task's change also shown by its ancestors is one event with them as sources; the prefix routing and the `(newValue, sender)` handler twins removed (`onAttributeChanged_Deprecated` is `on_attribute_changed`) | `taskcoachlib/domain/task/task.py`, `taskcoachlib/domain/effort/`, `taskcoachlib/domain/base/object.py`, `taskcoachlib/domain/base/sorter.py`; listeners in `taskcoachlib/gui/viewer/`, `taskcoachlib/gui/dialog/editor.py`, `attributesync.py`, `reminder.py`, `taskcoachlib/gui/taskbaricon.py`, `taskcoachlib/gui/scheduler.py`, `taskcoachlib/persistence/taskfile.py` |
| `effortlisttracker.changed` (the tracker's own pypubsub publisher) | Migrated to Publisher, the tracker as source | `taskcoachlib/domain/effort/effortlist.py` (EffortListTracker), `taskcoachlib/gui/idlecontroller.py`, `taskcoachlib/gui/uicommand/uicommand.py` (EffortStop) |
| `taskfile.aboutToRead`, `justRead`, `aboutToClear`, `justCleared`, `aboutToSave`, `dirty`, `clean`, `filenameChanged`, `changed` | Migrated to Publisher, the task file as source (a read-only merged file sends none); the viewers, main window and IO controller listen to their own file only | `taskcoachlib/persistence/taskfile.py`, `autosaver.py`, `autobackup.py`, `autoimporterexporter.py`, `taskcoachlib/gui/viewer/base.py`, `taskcoachlib/gui/mainwindow.py`, `taskcoachlib/gui/iocontroller.py`, `taskcoachlib/gui/uicommand/uicommand.py` (FileSave) |
| `command.aboutToBulkModify`, `command.justBulkModified` | Migrated to Publisher, the command as source (`_bulk_modification()`) | `taskcoachlib/command/taskCommands.py`, `taskcoachlib/gui/viewer/base.py` |
| `viewer<id>.status`, `viewer.status`, `all.viewer.status` | Migrated to Publisher: the viewer, or the container with the viewer as value, as source | `taskcoachlib/gui/viewer/base.py`, `container.py`, `effort.py`, `taskcoachlib/gui/status.py`, `taskcoachlib/gui/dialog/export.py` |
| `settings.<section>.<option>` | Replaced by the Publisher events `Settings.set()` already sent, plus a section event ([Settings Events](#settings-events)) | `taskcoachlib/config/settings.py`; listeners in `taskcoachlib/domain/task/task.py`, `taskcoachlib/gui/scheduler.py`, `taskcoachlib/gui/viewer/task.py`, `effort.py`, `taskcoachlib/gui/mainwindow.py` |
| pypubsub | Removed as a dependency: `setup.py`, the setup scripts, the CI workflows, the Debian, Fedora and Arch packaging, the Flatpak sources | |
| `task.reminder.trigger` | Migrated to Publisher | `taskcoachlib/domain/task/task.py` (Task), `taskcoachlib/gui/remindercontroller.py` (ReminderController) |
| `feature.task_duration_presets` | Migrated to Publisher | `taskcoachlib/gui/dialog/editor.py` (DatesPage) |
| `feature.effort_duration_presets` | Migrated to Publisher | `taskcoachlib/gui/dialog/editor.py` (EffortEditBook) |
| `timer.second` | Migrated to Publisher | `taskcoachlib/gui/scheduler.py` (GlobalTimer, MasterScheduler), `taskcoachlib/gui/taskbaricon.py`, `taskcoachlib/gui/dialog/editor.py` (BudgetPage, EffortEditBook), `taskcoachlib/gui/viewer/refresher.py` (SecondRefresher), `taskcoachlib/powermgt/idle.py` (IdleNotifier), `taskcoachlib/gui/mainwindow.py` (MainWindow, system theme check), `taskcoachlib/persistence/autosaver.py` (AutoSaver, retry) |
| `timer.minute` | Deleted (no subscribers; see `scheduler.minute`) | `taskcoachlib/gui/scheduler.py` |
| `timer.date` | Deleted (no subscribers; see `scheduler.date`) | `taskcoachlib/gui/scheduler.py` |
| `scheduler.dateChange.uiRefresh` | Replaced by Publisher `scheduler.date` | `taskcoachlib/gui/scheduler.py` (MasterScheduler), `taskcoachlib/domain/task/filter.py` (ViewFilter), `taskcoachlib/gui/viewer/task.py` (calendar viewers), `taskcoachlib/gui/viewer/base.py` (ViewerWithColumns) |
| `scheduler.minuteChange.uiRefresh` | Replaced by Publisher `scheduler.minute` | `taskcoachlib/gui/scheduler.py` (MasterScheduler), `taskcoachlib/gui/viewer/refresher.py` (MinuteRefresher), `taskcoachlib/gui/viewer/task.py` (calendar viewers) |

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

**Pattern:** change items only while the menu is closed, so GTK always
sees the correct geometry at popup time. Without messaging where possible:

- A **submenu** refills when its parent menu opens (the parent's
  `EVT_MENU_OPEN`, not its own): View's Mode/Filter/Columns/Sort/Rounding
  submenus, New > New task from template. Verified on GTK3: a refilled
  submenu is sized correctly on its first display.
- A **popup menu** refills just before `PopupMenu()`: the toolbar
  drop-downs (`PopupButtonMixin`), the tray (`popup_taskbar_menu`), the
  effort viewer's column header menu (`on_column_popup_menu`).
- Items directly in a **menu bar menu** have no earlier moment, so they
  follow a Publisher event that fires when the data changes (below).

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

## Settings Events

`Settings.set()` sends one Publisher event, the settings as source, of
two types: `"<section>.<option>"` with the new text as value, and
`Settings.section_changed_event_type(section)` (`"settings.<section>"`)
with the option's name as value, for listeners of a whole section (the
appearance sections, whose options are the statuses). Listeners read
typed values from the settings (`getint()`, `getboolean()`), not from
the event. `Settings.send_changed()` sends the same event without a
change: the main window uses it when the system theme changes while
the theme follows it.

---

**Last Updated:** September 2026
