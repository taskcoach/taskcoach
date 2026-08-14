# List Management Architecture

## Table of Contents

1. [TODO](#todo)
2. [Overview](#overview)
3. [Selection SSOT Principle](#selection-ssot-principle)
4. [Multi-Window Architecture](#multi-window-architecture)
5. [Select Next After Deletion](#select-next-after-deletion)
6. [Status Bar Updates](#status-bar-updates)
7. [Selection-Driven Button Enable/Disable](#selection-driven-button-enabledisable)
8. [Tree Mode Button Enable/Disable](#tree-mode-button-enabledisable)
9. [Scroll After Rebuild (Tree Views)](#scroll-after-rebuild-tree-views)
10. [Windows: Scrollbar Adjustment on Content Changes](#windows-scrollbar-adjustment-on-content-changes)
11. [Row Hover Outline](#row-hover-outline)
10. [Mouse-Move Handler Inventory (Tree Views)](#mouse-move-handler-inventory-tree-views)
11. [Vampire CPU Usage](#vampire-cpu-usage)
12. [AUI Sash Resize Throttle](#aui-sash-resize-throttle)
13. [AUI Repaint Cascade on GTK3](#aui-repaint-cascade-on-gtk3)
14. [Key Files](#key-files)

---

## TODO

1. **Selection highlight outline:** Add the same two-tone border outline
   (currently used for hover) around the currently selected row(s) as well.
   This would provide a stronger, more accessible visual indicator for
   selection — especially on low-contrast themes or when custom row colors
   make the default selection highlight hard to see. The hover outline
   infrastructure (`_hoverItem`, `PaintLevel`, `_refresh_hover_row`) could be
   reused or extended to also draw around selected items using a different
   color pair (e.g. `SYS_COLOUR_HIGHLIGHT` / `SYS_COLOUR_HIGHLIGHTTEXT`).
2. ~~**Eliminate UpdateUI polling entirely**~~: **Done.** All `EVT_UPDATE_UI`
   bindings removed from UICommand. Replaced by signal-driven `_SelectionSync`
   and `_ViewSettingsSync` classes. See [Vampire CPU Usage](#vampire-cpu-usage)
   for background.

---

## Overview

Task Coach uses multiple viewer windows that can display the same underlying data. This document describes how list selection, refresh, and coordination between windows works.

---

## Selection SSOT Principle

**Single Source of Truth:** The widget is the source of truth for selection state.

**Reference:** `base.py:curselection()` - always returns `widget.curselection()` fresh.

**Key points:**
- No selection cache for reads
- Always query widget when selection is needed
- Commands get fresh selection when user triggers action
- Status bar queries fresh after its 500ms debounce

---

## Multi-Window Architecture

Multiple viewers can show the same data (e.g., two task list windows). When data changes:

```
Domain layer changes (e.g., task deleted)
    │
    ▼
onPresentationChanged() fires to ALL viewers
    │
    ├── Window A receives event
    │   └── Handles based on its own widget state
    │
    └── Window B receives event
        └── Handles based on its own widget state
```

Each window independently:
1. Refreshes its display
2. Checks its own selection state
3. Takes action if needed (e.g., select next item)

---

## Select Next After Deletion

When items are deleted and the selection becomes empty, select the "next" item for better UX (accessibility best practice).

### The Timing Problem

```
onPresentationChanged(event):
    │
    ├── BEFORE refresh(): Widget has old state (deleted items still visible)
    │   └── Can query: selected items, their positions
    │
    ├── refresh(): Widget updates
    │
    └── AFTER refresh(): Deleted items gone, positions shifted
        └── Cannot determine where deleted items were
```

### Solution: Capture State Before Refresh

**Reference:** `base.py:onPresentationChanged()`, `_captureSelectionInfo()`, `selectNextItemsAfterRemoval()`

Flow:
1. BEFORE refresh: call `_captureSelectionInfo()` to get parent and index
2. Call `refresh()` - widget updates, deleted items gone
3. AFTER refresh: if selection empty, call `selectNextItemsAfterRemoval(selectionInfo)`

### Edge Cases

**Deleted from bottom of list:**
- Selected item was at index N
- After deletion, list only has M items where M < N
- Select last item: `min(len(siblings) - 1, index)` = last item

**Parent also deleted:**
- Check if parent still in presentation
- If not, look for siblings at root level

**Benefits:**
- No cache maintained on every selection change
- State captured only when needed (before refresh on removal)
- Each window captures its own state independently

---

## Status Bar Updates

Status bar displays info about current selection. Uses debouncing to avoid excessive updates.

### Event Flow

```
Selection changes in widget
    │
    ▼
onSelect() fires
    │
    ▼
sendViewerStatusEvent() - fires pubsub event
    │
    ▼
StatusBar receives event, restarts 500ms timer
    │
    ▼
After 500ms of no changes:
    │
    ▼
StatusBar queries curselection() - gets fresh data
    │
    ▼
StatusBar displays status
```

**Key point:** Selection is queried ONCE, only when actually displaying (after debounce).

---

## Selection-Driven Button Enable/Disable

See [MENUS.md](MENUS.md) for the menu-side architecture (MenuItem subclass,
`_update_menu_state()`, menu-level state methods).

Toolbar and menu commands that depend on selection state (Edit, Delete, Cut,
Copy, etc.) update their enabled state via Publisher signal — not polling.
The viewer computes selection state once on selection change and fires a
per-instance event. Each command subscribes directly.

This replaces the former `EVT_UPDATE_UI` polling pattern where ~15 buttons
called `curselection()` (walking `GetSelections()` + `GetItemPyData()`)
every 200ms. See [Vampire CPU Usage](#vampire-cpu-usage) for the full
problem description.

### Signal Flow

```
EVT_TREE_SEL_CHANGED / EVT_LIST_ITEM_SELECTED / DESELECTED
    └── widget.onSelect()
        └── selectCommand() → viewer.onSelect()
            ├── patterns.Event(selection_changed_event_type, self, has_selection).send()
            │   └── _SelectionSync._on_selection_changed(event)
            │       └── toolbar.EnableTool(id, command.enabled(None))
            └── wx.CallAfter(sendViewerStatusEvent)  [existing]
```

### Design

**Viewer** (`base.py`): Fires a Publisher event on selection change using
a per-instance event type (`selection_changed_event_type()`). Same pattern as
the tree mode toggle — see
[PUBLISHER_OBSERVER.md — Case Study: Tree Mode Toggle](PUBLISHER_OBSERVER.md#case-study-tree-mode-toggle).

**Helper** (`_SelectionSync` in `uicommand.py`): A small wiring object
that subscribes to the viewer's selection signal via `registerObserver`
and calls `command.enabled()` → `toolbar.EnableTool()` on change. Each
command creates one in its `append_to_toolbar`.

**Commands**: Each selection-dependent command overrides `onUpdateUI` as
a no-op, creates a `_SelectionSync` in `append_to_toolbar`, and owns its
`enabled()` check. Signal handlers and menu open both call
`command.enabled()` — one source of truth.

### Key Files

| File | Role |
|------|------|
| `taskcoachlib/gui/viewer/base.py` | Cache, properties, Publisher event |
| `taskcoachlib/gui/uicommand/uicommand.py` | `_SelectionSync`, command wiring |
| `taskcoachlib/gui/uicommand/base_uicommand.py` | `MenuItem` subclass, `UICommand` base |

---

## Tree Mode Button Enable/Disable

See [MENUS.md](MENUS.md) for the menu-side architecture.

The Expand All and Collapse All toolbar buttons are only meaningful in tree
mode. Their enabled state is driven by a Publisher signal from the viewer —
the same per-instance pattern used for
[selection-driven buttons](#selection-driven-button-enabledisable).

### Signal Flow

```
Toolbar Dropdown / Menu Radio
    └── viewer.set_tree_mode(value)  (task.py)
        ├── settings.setboolean(...)          ← persistence
        ├── presentation().set_tree_mode(value) ← data layer
        └── patterns.Event(view_settings_changed_event_type, self).send()
            ├── _ViewSettingsSync._on_view_settings_changed(event)
            │   └── toolbar.EnableTool(id, command.enabled(None))
            └── TaskViewerTreeOrListChoice._on_view_settings_changed(event)
                └── set_choice(settings.getboolean(..., "treemode"))
```

### Design

**Viewer** (`task.py`): `set_tree_mode(value)` writes the setting, updates
the presentation, and fires a per-instance Publisher event via
`view_settings_changed_event_type()` (defined in `base.py`). The event
carries no data — receivers read current state from the viewer/settings.

**Helper** (`_ViewSettingsSync` in `uicommand.py`): Sets the
initial enabled state via `command.enabled()`, then subscribes to
the viewer's settings event via `registerObserver`. On change, calls
`command.enabled()` → `toolbar.EnableTool()`.

**Commands**: `ViewExpandAll` and `ViewCollapseAll` each create a
`_ViewSettingsSync` in `append_to_toolbar` and override `onUpdateUI`
as a no-op (these buttons are fully signal-driven).

**Dropdown**: `TaskViewerTreeOrListChoice` subscribes to the same signal
and reads the current treemode value from settings on change.

### Key Files

| File | Role |
|------|------|
| `taskcoachlib/gui/viewer/task.py` | `set_tree_mode()`, fires Publisher event |
| `taskcoachlib/gui/viewer/base.py` | `view_settings_changed_event_type()` |
| `taskcoachlib/gui/uicommand/uicommand.py` | `_ViewSettingsSync`, `ViewExpandAll`, `ViewCollapseAll`, `TaskViewerTreeOrListChoice` |

---

## Scroll After Rebuild (Tree Views)

### Problem

After filter changes, search clears, or category toggles, the selected item scrolls off-screen in tree views. The user must press arrow keys to find it.

### Root Cause

HyperTreeList's `ScrollTo()` (upstream, in `hypertreelist.py`) calls `CalculatePositions()` when `_dirty` but never calls `AdjustMyScrollbars()`. During normal use (click, keyboard), scrollbars are already current. But after a freeze/thaw rebuild cycle (`RefreshAllItems` in `treectrl.py`), the scrollbar range is stale. `Scroll()` gets clamped to the old range and silently does nothing.

This is an upstream design limitation (same in wxPython 4.2.0 and current master), not a bug in our code.

**Does NOT affect list views** — `VirtualListCtrl` uses native wx scrollbar management.

### Fix: Two Scroll Methods

Both methods live on the tree control subclass in `treectrl.py`. Both call `AdjustMyScrollbars()` before scrolling to fix the stale range.

**`scroll_to_selection()`** - Minimal scroll to make first selected item visible.
- Called from: `treectrl.py:RefreshAllItems()` - fires for ALL callers (init, file load, expand/collapse, sort, etc.)
- Reference: `treectrl.py:TreeListCtrl.scroll_to_selection`

**`scroll_to_selection_centered()`** - Centers viewport on first selected item.
- Called from: `base.py:on_presentation_changed()` - fires only on add/remove events (filter toggle, search, category filter)
- Overrides the position set by `scroll_to_selection()` in the same flow
- Reference: `treectrl.py:TreeListCtrl.scroll_to_selection_centered`

### Flow

**Filter toggle / search / category filter / add / delete** — fires add/remove events:
```
on_presentation_changed (base.py)
  -> refresh()
    -> widget.RefreshAllItems() (treectrl.py)
      -> Freeze -> DeleteAll -> Add -> Thaw -> restore selection
      -> scroll_to_selection()                 (ensure-visible)
  -> scroll_to_selection_centered()            (center on selected)
```

**Mode switch (list <-> tree)** - fires sort event, NOT add/remove:
```
viewer.set_tree_mode(value) (task.py)
  -> settings.setboolean(...)                (persistence)
  -> presentation().set_tree_mode(value)
    -> Sorter.reset() -> fires sort_event_type (NOT add/remove)
      -> on_sort_order_changed (mixin.py) -> refresh()
        -> widget.RefreshAllItems()
          -> scroll_to_selection()           (ensure-visible, selection-gated)
  -> widget._schedule_scrollbar_adjustment() (recompute range, deferred on Windows)
  -> scroll_to_selection_centered()          (center on selected, selection-gated)
  -> patterns.Event(...).send()              (Publisher event)
    -> dropdown: set_choice(value)
    -> buttons: EnableTool(id, value)
```
Note: `Sorter.reset()` fires `pub.sendMessage(self.sort_event_type())`, not add/remove
events, so `on_presentation_changed` does NOT fire. Because the rebuild's own recompute
(`scroll_to_selection`) is synchronous and gated on a non-empty selection, `set_tree_mode`
also calls `_schedule_scrollbar_adjustment()` to recompute the scrollbar range
unconditionally (deferred on Windows). The Publisher event syncs the toolbar dropdown and
expand/collapse buttons, see [PUBLISHER_OBSERVER.md - Case Study: Tree Mode Toggle](PUBLISHER_OBSERVER.md#case-study-tree-mode-toggle)
for the full signal flow.

### Scroll Behavior by User Action

All tree-based viewers (task tree, category tree, note tree) follow this table.
List-only viewers (effort, attachments) always use `ensureSelectionVisible` (native wx).

| User Action                     | Scroll Behavior | Path                                     |
|---------------------------------|-----------------|------------------------------------------|
| Toggle status filter            | Center          | `on_presentation_changed` -> centered    |
| Toggle category filter          | Center          | `on_presentation_changed` -> centered    |
| Clear/change search text        | Center          | `on_presentation_changed` -> centered    |
| Switch list <-> tree mode       | Center          | `set_tree_mode` -> `_schedule_scrollbar_adjustment` (range) + centered |
| Delete selected item            | Center          | `on_presentation_changed` -> centered    |
| Add new item                    | Center          | `on_presentation_changed` -> centered    |
| Window resize                   | Center          | `EVT_SIZE` -> `CallAfter` -> centered    |
| Sort change                     | Ensure-visible  | `refresh()` only, no `on_presentation_changed` |
| Expand all / Collapse all       | Ensure-visible  | `refresh()` only, no `on_presentation_changed` |
| Item edit (attribute change)    | No scroll       | `RefreshItems()`, not `RefreshAllItems`  |
| File load                       | Ensure-visible  | `onEndIO` → `refresh()` only             |
| Initial startup                 | Ensure-visible  | `__init__` → `refresh()` only            |

**Center** = `scroll_to_selection_centered()` - viewport centers on first selected item
**Ensure-visible** = `scroll_to_selection()` - minimal scroll, just makes item visible
**No scroll** = individual rows refreshed in place, no scroll change

### Auto-Scroll Toggle

Every behavior in the table above is gated by the global boolean setting
`view.autoscrollselection` (default `True`), toggled by the
`ToggleAutoScroll` UI command: a stay-pressed check button on the main
toolbar and the task viewer toolbar (icon
`oxygen_actions_align-vertical-center`) plus a check item in the View
menu.

When the setting is `False` ("stable" mode, the view never scrolls by
itself):

- `scroll_to_selection_centered()` returns early. This covers the
  presentation-change, tree/list mode switch, and window resize paths.
- `_do_full_rebuild()` saves `GetViewStart()` before the rebuild and
  restores it afterwards instead of calling `scroll_to_selection()`.
  The restore also cancels the implicit `EnsureVisible` that restoring
  the selection triggers in upstream `customtreectrl`.
- `VirtualListCtrl.ensureSelectionVisible()` returns early (list views).

User-initiated scrolling (mouse click, keyboard navigation) is not
affected. When the setting is turned back on, each viewer re-centers
its widget on the selection immediately
(`Viewer.on_auto_scroll_changed` in `viewer/base.py`). The toolbar
buttons stay in sync with each other and with the menu the same way
(`ToggleAutoScroll._on_setting_change`). Both use legacy Publisher
dispatch (`registerObserver` on event type `view.autoscrollselection`
with the settings object as source), not pypubsub; see
PUBLISHER_OBSERVER.md for why new signals must not use pubsub.

---

## Windows: Scrollbar Adjustment on Content Changes

### Problem

On Windows, tree/list viewer scrollbars do not update when expanding/collapsing/adding/deleting tasks, or switching between tree and list views. Scrollbars only update on window resize. This does not occur on Linux/GTK or macOS.

### Root Cause

The scrollbar range is only ever recomputed by `AdjustMyScrollbars()`, and that recompute is gated. On the expand path it runs only through the upstream `RefreshSubtree()`, which returns early when the tree is marked dirty or frozen. `AdjustMyScrollbars()` itself becomes a no-op (it just sets the dirty flag) while frozen, and the dirty flag is cleared only by the upstream `OnInternalIdle()`. On a settled GTK tree the recompute fires synchronously, which is why Linux is unaffected. On Windows the recompute is missed when content changes while the tree is dirty or frozen, or before idle runs, and a synchronous `AdjustMyScrollbars()` does not reliably take effect until after the layout cycle. Deferring the call (see below) lets it run after that dirty/frozen state has cleared.

### Fix: Deferred Scrollbar Adjustment

A new method `_schedule_scrollbar_adjustment()` on `TreeListCtrl` (`treectrl.py`) handles the platform difference:

- **Windows**: Uses `wx.CallAfter()` to defer scrollbar adjustment until after the event queue empties and the layout/idle cycle has cleared the dirty/frozen state
- **Other platforms**: Adjusts immediately (the deferral is harmless and ensures consistency)

Called from:
- `_expandDropTarget()` — after explicit expand on drag-drop
- `on_item_expanding()` — after lazy-loading children when item expands
- `TreeViewer.on_item_expanded()` / `on_item_collapsed()` — after individual expand/collapse events
- `TreeViewer.expand_all()` / `collapse_all()` — after bulk expand/collapse operations
- `_refresh_all_items_in_place()` — after in-place content refresh without tree rebuild
- `TaskViewer.set_tree_mode()` — after a tree<->list switch (see note below)

#### Why the tree<->list switch needs its own call

Switching mode rebuilds the widget through `_do_full_rebuild()`, whose only scrollbar recompute is `scroll_to_selection()` / `scroll_to_selection_centered()`. Both are **synchronous** and **gated on `if selections:`** (`treectrl.py`), so on Windows the range is not recomputed reliably (synchronous adjustment misses the post-layout cycle, and an empty selection skips it entirely). Unlike add/delete, the switch fires a sort event rather than an add/remove event, so `on_presentation_changed()` never runs and never supplies its own adjustment. `set_tree_mode()` therefore calls `_schedule_scrollbar_adjustment()` explicitly — the deferred, unconditional adjustment that already fixes the other cases. This was the one path that remained broken on Windows after the initial fix; confirmed fixed by Windows testing.

### Scroll Behavior (Updated Table)

All tree-based viewers now adjust scrollbars consistently on all platforms:

| User Action                     | Scroll Behavior | Windows | Other Platforms |
|---------------------------------|-----------------|---------|-----------------|
| Expand single item              | Ensure-visible  | Deferred via `CallAfter` | Immediate |
| Collapse single item            | Ensure-visible  | Deferred via `CallAfter` | Immediate |
| Expand all                      | Ensure-visible  | Deferred via `CallAfter` | Immediate |
| Collapse all                    | Ensure-visible  | Deferred via `CallAfter` | Immediate |
| Switch tree <-> list            | Center          | Deferred via `CallAfter` | Immediate |

(Other scroll behaviors unchanged — see previous table above)

### Related Issues

See [Scroll After Rebuild (Tree Views)](#scroll-after-rebuild-tree-views) for scrollbar stale-range issues after freeze/thaw rebuild cycles.

---

## Row Hover Outline

A two-tone (fg/bg) hover outline on all list and tree view rows, following the
W3C WCAG C40 technique used by Chrome/Edge focus indicators. An inner line uses
`SYS_COLOUR_WINDOWTEXT` and an outer line uses `SYS_COLOUR_WINDOW`, guaranteeing
visibility on any background including selected, custom-colored, and unfocused
rows. Line thickness is configurable via **Preferences > Theme > Hoverover
Highlight** (default 1, 0 to disable). Read directly via
`settings2.window.hoverlinewidth` at every use site — no cached attribute,
changes take effect immediately without restart.

Tooltips are controlled by `settings2.view.descriptionpopups` (bool), read
directly on every mouse-move in `ToolTipMixin.__OnMotion`. The expensive
`OnBeforeShowToolTip()` call (HitTest + full tooltip data extraction traversing
notes, categories, attachments, descriptions) is deferred to a 200ms timer
callback. Only the mouse position is stored on motion; data extraction runs
once after the cursor is still.

### Two-Tone Strategy (W3C WCAG C40)

The outline uses two contrasting 1px lines — inner `SYS_COLOUR_WINDOWTEXT` (fg)
and outer `SYS_COLOUR_WINDOW` (bg) — so at least one line is always visible
regardless of the row's background color (normal, selected, custom, focused or
unfocused). This is the same technique Chrome/Edge use for keyboard focus
indicators.

Reference: [W3C WCAG Technique C40 — Creating a two-color focus indicator to
ensure sufficient contrast](https://www.w3.org/WAI/WCAG21/Techniques/css/C40)

### Tree Views (HyperTreeList)

```
EVT_MOUSE_EVENTS on TreeListMainWindow
    │
    ├── OnMouse() fast-path (hypertreelist.py)
    │   └── event.Moving() and not dragging?
    │       ├── Same row (Y-bounds cache hit) → return (zero work)
    │       └── New row → HitTest → SetHoverItem(item)
    │           ├── _refresh_hover_row(prevItem)      ← padded invalidation
    │           │   └── settings2.window.hoverlinewidth  ← direct read
    │           └── _refresh_hover_row(newItem)       ← padded invalidation
    │               └── settings2.window.hoverlinewidth  ← direct read
    │
    └── event.Skip() → tooltip __OnMotion fires (tooltip.py)
        └── settings2.view.descriptionpopups        ← direct read
            └── start 200ms timer → OnBeforeShowToolTip
```

**State:** `TreeListMainWindow._hoverItem` — the currently hovered item, or `None`.

**Drawing:** In `PaintLevel()` in `hypertreelist.py`, after row lines and before
DC restore. Draws outer 1px bg rect (inflated by 1), then inner 1px fg rect.
Skipped for drag items.

**Cleanup:** `EVT_LEAVE_WINDOW` → `SetHoverItem(None)`.

**Ghosting prevention:** `_refresh_hover_row()` inflates the invalidation rect by
3px (1px inner + 1px outer + safety) so the full two-tone outline is erased on
repaint.

### List Views (VirtualListCtrl)

```
EVT_MOTION on VirtualListCtrl
    │
    ├── _on_hover_motion()
    │   └── HitTest → row != _hover_row?
    │       ├── settings2.window.hoverlinewidth?   ← direct read
    │       │   ├── _refresh_hover_row(old)   ← padded invalidation
    │       │   └── _refresh_hover_row(new)   ← padded invalidation
    │       │   └── CallAfter(_draw_hover_outline)
    │       │       └── settings2.window.hoverlinewidth  ← direct read
    │
    └── event.Skip() → tooltip __OnMotion fires (tooltip.py)
        └── settings2.view.descriptionpopups        ← direct read
            └── start 200ms timer → OnBeforeShowToolTip
```

Native `wx.ListCtrl` has no PaintItem hook, so the outline is drawn post-paint
via `wx.ClientDC` + `wx.CallAfter`. `EVT_PAINT` also triggers a deferred redraw
to survive native repaints.

**Cleanup:** `EVT_LEAVE_WINDOW` → reset `_hover_row`, padded refresh.

### Settings

Both hover and tooltip settings are read directly via the `settings2` shim
(see [SETTINGS.md](SETTINGS.md)) — no cached attributes, no getter lambdas,
no pubsub subscriptions.

- `settings2.window.hoverlinewidth` — integer, default 1. 0 disables hover,
  >0 enables the two-tone outline. User-facing: **Preferences > Theme >
  Hoverover Highlight**.
- `settings2.view.descriptionpopups` — boolean, default True. Enables/disables
  tooltip popups. User-facing: **Preferences > View > Description popups**.

---

## Mouse-Move Handler Inventory (Tree Views)

Only two handlers fire on mouse motion. Both call `event.Skip()` so the chain is not broken.

| Handler | File | Purpose |
|---------|------|---------|
| `OnMouse` fast-path | `hypertreelist.py` | Row-bounds cache → HitTest only on row change → update `_hoverItem`, read `settings2.window.hoverlinewidth` |
| `__OnMotion` (ToolTipMixin) | `tooltip.py` | Read `settings2.view.descriptionpopups`, store position, start 200ms timer |
| `__OnTimer` (ToolTipMixin) | `tooltip.py` | Call `OnBeforeShowToolTip()` → build tooltip |

**Hover fast-path:** `OnMouse` short-circuits for `event.Moving()` before the
full HitTest + button/drag/tooltip processing (~200 lines skipped). A Y-bounds
cache skips HitTest entirely when the mouse stays on the same row.

**Drag fast-path:** During drag, a row+column bounds cache skips HitTest when
the mouse stays on the same cell. Only `dragImage.Move()` runs per pixel.

**Tooltip:** `OnBeforeShowToolTip()` (which does HitTest + `getItemTooltipData()`
traversing notes, categories, attachments, descriptions) is deferred to the timer
callback. On every mouse move, only the position is stored and the timer restarted.
The expensive data extraction runs once after 200ms of stillness.

**Removed:** `_on_hover_motion` (was in `treectrl.py`) — performed a duplicate
HitTest on every pixel. Hover tracking is now integrated into `OnMouse` fast-path.

---

## Vampire CPU Usage

wx's default `EVT_UPDATE_UI` mechanism is a polling loop that silently
consumes CPU even when the application is minimized and the user is doing
nothing.

### The Problem

Two always-running repeating timers keep the wx event loop alive:

| Timer | File | Interval | Purpose |
|-------|------|----------|---------|
| Signal check | `application.py:801` | 500ms | Wakes event loop so SIGINT/SIGTERM work (Linux/Mac) |
| Global scheduler | `scheduler.py:88` | 1000ms | Fires `timer.second` for reminders, effort tracking |

Every timer tick generates an event. After each event, wx fires `EVT_IDLE`.
During idle, wx fires `EVT_UPDATE_UI` for **every visible toolbar button**
(~30 items across all viewer toolbars). Each one calls `enabled()` to check
whether the button should be greyed out.

```
signal_check_timer fires (every 500ms)
  -> event queue briefly empty -> EVT_IDLE fires
  -> wx checks: interval elapsed since last UpdateUI? yes
  -> EVT_UPDATE_UI x ~30 visible toolbar buttons
  -> each calls enabled() to poll state
  -> repeat forever, even when minimized
```

This happens even when no state has changed, because UpdateUI is a **polling**
mechanism — it re-checks every button on every idle cycle regardless.

### What `enabled()` actually does

Each `onUpdateUI` call runs `event.Enable(bool(self.enabled(event)))`. For
simple commands like `FileOpen` this is a trivial `return True`. But ~15 of the
~30 toolbar buttons inherit `NeedsSelectionMixin`, which does real work:

```python
# mixin_uicommand.py — NeedsSelectionMixin
def enabled(self, event):
    return super().enabled(event) and self.viewer.curselection()

# base.py — Viewer.curselection()
def curselection(self):
    return self.widget.curselection()  # walks GetSelections() on the tree
```

So for NewSubItem and others still using mixin-based polling, every 200ms wx:

1. Calls `widget.curselection()` → iterates all selected tree items → maps
   each to a domain object via `GetItemPyData()`
2. Some also checked viewer type via `is_task`, `is_note`, etc. properties
   (previously `curselectionIsInstanceOf()` — now removed)

All to answer "should this button be greyed out?" — when nothing has changed.
This is pure waste. The correct approach would be event-driven: update button
states only when selection or data actually changes, not by continuous polling.

### ~~TODO~~: Eliminate UpdateUI polling entirely — DONE

**Q1: Can we piggyback on the 1-second scheduler tick?** The global scheduler
timer already fires every second (`scheduler.py:88`). Instead of wx polling
`enabled()` via UpdateUI, we could update toolbar button states once per second
in the scheduler callback. This would consolidate the work into one place and
eliminate the UpdateUI overhead entirely.

**Q2: Can we make it event-driven instead?** Selection changes already fire
`EVT_TREE_SEL_CHANGED` → `onSelect()`. Data changes fire
`onPresentationChanged()`. Undo/redo state changes when commands execute. We
could call `UpdateWindowUI()` explicitly at these points and disable the
polling entirely via `wx.UpdateUIEvent.SetMode(wx.UPDATE_UI_PROCESS_SPECIFIED)`.
This way button states update immediately on real changes and never poll.

**Q3: Why are static buttons being polled?** Buttons like `FileOpen`, `Print`,
`TaskNew`, `ViewExpandAll`, `ViewCollapseAll` are **always enabled** — their
`enabled()` just returns `True`. Yet wx polls them every 200ms anyway. These
should either be excluded from UpdateUI entirely (don't bind `EVT_UPDATE_UI`
for them) or their `onUpdateUI` should be a no-op that skips `event.Enable()`.

**Q4: Why grey out buttons at all?** The simplest fix: keep all buttons always
enabled and make `do_command()` no-op when the action doesn't apply (no
selection, wrong item type, etc.). This eliminates the entire UpdateUI
mechanism — no polling, no `enabled()` calls, no `EVT_UPDATE_UI` bindings,
zero idle CPU. The greyed-out visual is a minor UX hint that doesn't justify
continuous CPU polling. Clicking "Delete" with nothing selected simply does
nothing. This is how many modern apps work (e.g. VS Code toolbar buttons
don't grey out). The `do_command()` methods already guard against invalid state
in many cases via `on_command_activate()` which checks `self.enabled(event)`.

**Recommended approach (Option A — simplest):** Make all buttons always enabled.
Remove all `EVT_UPDATE_UI` bindings from `bind()` in `base_uicommand.py`. Keep
the `enabled()` check inside `on_command_activate()` so commands still no-op
when they don't apply. Remove `SetUpdateInterval` since it's no longer needed.
This is the simplest change with the largest impact — eliminates the entire
UpdateUI polling loop in one stroke.

**Alternative approach (Option B — event-driven):** Combine Q2 and Q3. Remove
`EVT_UPDATE_UI` bindings from always-enabled buttons (Q3). For the rest, switch
to `UPDATE_UI_PROCESS_SPECIFIED` mode and explicitly trigger
`UpdateWindowUI()` on selection change, data change, and undo/redo (Q2). The
`SetUpdateInterval(200)` stays as a safety fallback. This preserves the
greyed-out visual feedback for context-sensitive buttons while eliminating the
continuous polling overhead.

### Button Inventory by Update Mechanism

**Signal-driven** (no `EVT_UPDATE_UI`, no polling):

| Command | Signal | What drives enable/disable |
|---------|--------|---------------------------|
| `EditCut` | selection | `_SelectionSync` → `command.enabled()` |
| `EditCopy` | selection | `_SelectionSync` → `command.enabled()` |
| `ClearSelection` | selection | `_SelectionSync` → `command.enabled()` |
| `Edit` | selection | `_SelectionSync` → `command.enabled()` |
| `Delete` | selection | `_SelectionSync` → `command.enabled()` |
| `Mail` | selection | `_SelectionSync` → `command.enabled()` |
| `ViewExpandAll` | view settings | `_ViewSettingsSync` → `command.enabled()` |
| `ViewCollapseAll` | view settings | `_ViewSettingsSync` → `command.enabled()` |
| `TaskMarkActive` | selection | `_SelectionSync` → `command.enabled()` |
| `TaskMarkInactive` | selection | `_SelectionSync` → `command.enabled()` |
| `TaskMarkCompleted` | selection | `_SelectionSync` → `command.enabled()` |
| `EffortStart` | selection | `_SelectionSync` → `command.enabled()` |
| `EffortStartForEffort` | selection | `_SelectionSync` → `command.enabled()` |
| `EffortNew` | selection | `_SelectionSync` → `command.enabled()` |
| `EditPasteAsSubItem` | selection | menu-open → `command.enabled()` |
| `ResetFilter` | filter change | `Filter.filter_change_event_type()` → `command.enabled()` |
| `ViewerHideTasks` | filter change | `Filter.filter_change_event_type()` → `command.checked()` |
| `SelectAll` | selection | menu-open → `command.enabled()` |
| `ToggleCategory` | selection | menu-open → `command.enabled()` + `checked()` |
| `FileSave` | dirty state | `taskfile.dirty`/`taskfile.clean` pubsub → `command.enabled()` |
| `FileMergeDiskChanges` | disk change | `taskfile.changed`/dirty/clean pubsub → `command.enabled()` |
| `FilePurgeDeletedItems` | deleted items | menu-open → `command.enabled()` |
| `ViewerHideCompositeTasks` | tree mode | menu-open → `command.enabled()` + `checked()` |
| `EditTrackedTasks` | tracking | menu-open → `command.enabled()` |
| `EditUndo` | history | `commandhistory.changed` pubsub → `command.enabled()` |
| `EditRedo` | history | `commandhistory.changed` pubsub → `command.enabled()` |

**Custom `enabled()`** (`EVT_UPDATE_UI` but no selection polling):

| Command | What `enabled()` checks |
|---------|-------------------------|
| `EditPaste` | `TextCtrl.CanPaste()` or clipboard |
| `RenameViewer` | `activeViewer()` |
| `ActivateViewer` | `viewerCount() > 1` |
| `HideCurrentColumn` | `isHideableColumn()` at mouse position |
| `EffortStartForTask` | task not completed/tracked |
| `EffortStartButton` | any task not completed |
| `DialogCommand` | dialog is closed |
| `Anonymize` | `iocontroller.filename()` |

### Additional idle handlers that fire on every cycle

| Handler | File | Cost |
|---------|------|------|
| `onIdle` | `taskbaricon.py:124` | Compares tooltip text + icon strings |
| `_OnIdle` | `powermgt/idle.py:401` | Two `time.time()` calls + state check |
| `_on_idle` | `windowdimensionstracker.py:469` | Checks ready flag (cheap early return) |

### The Fix: SetUpdateInterval

`wx.UpdateUIEvent.SetUpdateInterval(200)` in `application.py:OnInit` throttles
UpdateUI processing to fire at most every 200ms instead of on every idle cycle.
This is wx's official recommended API for this exact problem.

**Before:** ~30 `enabled()` calls on every idle cycle (hundreds/sec during
mouse motion, ~2/sec when idle via timer ticks).

**After:** ~30 `enabled()` calls at most every 200ms (~5 batches/sec max),
regardless of how many idle cycles occur.

### Why only toolbar items, not menu items?

wx only fires `EVT_UPDATE_UI` for **currently visible** UI elements. Toolbar
buttons are always visible, so they get polled continuously. Menu items only
receive UpdateUI **when the menu is opened**. This is why the log shows only
toolbar button names (TaskNew, Edit, Delete, EffortStart, etc.) and not the
full set of 48+ UICommand subclasses.

Duplicate entries (ResetFilter x2, EditToolBarPerspective x3, EffortStop x2)
appear because those buttons exist on **multiple viewer toolbars** — each
viewer panel has its own toolbar with its own bindings.

### Debug logging points (removed — documented for reference)

The following `log_step()` probes were inserted to diagnose the CPU usage and
then removed. Re-add any of them to trace a specific path:

| Probe | File:line | Prefix | What it traces |
|-------|-----------|--------|----------------|
| OnMouse same-row | `hypertreelist.py:OnMouse` fast-path | `OnMouse` | Mouse motion within same row (should be majority) |
| OnMouse new-row | `hypertreelist.py:OnMouse` fast-path | `OnMouse` | Mouse crossing to a new row (triggers HitTest) |
| OnMouse fallthrough | `hypertreelist.py:OnMouse` after fast-path | `OnMouse` | Non-motion events (clicks, drag) entering full handler |
| Tooltip motion | `tooltip.py:__OnMotion` | `TOOLTIP` | Timer stop/restart on every mouse move |
| UpdateUI poll | `base_uicommand.py:onUpdateUI` | `UpdateUI` | Each toolbar button's enabled() poll |
| Taskbar idle | `taskbaricon.py:onIdle` | `EVT_IDLE` | Tray icon tooltip/icon string comparison |
| Power mgmt idle | `powermgt/idle.py:_OnIdle` | `EVT_IDLE` | Idle-time state machine check |
| Window dims idle | `windowdimensionstracker.py:_on_idle` | `EVT_IDLE` | Window position/size readiness check |
| Autosaver idle | `autosaver.py:on_idle` | `EVT_IDLE` | Dirty-file save during idle |

### All Repeating Timers

| Timer | File | Interval | Always? | Purpose |
|-------|------|----------|---------|---------|
| Signal check | `application.py:801` | 500ms | Yes (Linux/Mac) | SIGINT/SIGTERM handling |
| Global scheduler | `scheduler.py:88` | 1000ms | Yes | Reminders, effort display |
| Effort refresher | `refresher.py:146` | 1000ms | Only while tracking | Updates effort time display |
| Notification center | `notifier_universal.py:294` | 1000ms | While notifications shown | Timeout-based dismissal |
| Notification anim | `notifier_universal.py:44,91` | 100ms | During fade-in only (~1s) | Fade-in/move animation |
| Editor time spent | `editor.py:4240` | 1000ms | While editor open + tracking | Time spent display |
| Editor Mac poll | `editor.py:4457` | 1000ms | macOS only, editor open | Window close detection |

Only the first two (signal check, global scheduler) run at all times. All
others are conditional and stop when their context ends.

---

## AUI Sash Resize Throttle

AUI's `LIVE_RESIZE` mode calls `Update()` on every mouse move during sash drag, which triggers expensive `DoUpdate` repaints (50-190ms). A throttle wrapper in `frame.py` (`_install_sash_resize_optimization`) limits updates to ~30fps during sash drag (action == 3) to reduce CPU load and flickering.

---

## AUI Repaint Cascade on GTK3

### The Problem

`agw.aui.AuiManager` enters a repaint cascade on GTK3 after tree/list
rebuilds.  Without mitigation, this adds 880–1290ms of UI latency.

### Root Cause

**Mouse movement over the app during/after a rebuild drives the
cascade.**  Each mouse motion event triggers AuiManager processing
(hit testing, pane button hover via `RefreshButton` → `frame.Refresh()`
+ `frame.Update()`).  Each forced frame repaint draws AUI chrome
(borders, captions, sashes) over child widget areas via `OnRender`,
which triggers GTK3 GdkWindow damage propagation on child windows,
which re-invalidates the frame, creating a self-sustaining cycle.

The cascade is NOT non-deterministic — it is **determined by mouse
position and movement** relative to the app window.  Toolbar toggle
is fast (mouse stays on toolbar); menu toggle varies (depends on mouse
position after menu dismiss).

### Current Solution (2 layers)

**1. Synchronous rebuild** (`treectrl.py`):
`_do_full_rebuild()` is synchronous: Freeze, delete, rebuild, Thaw,
`Refresh(eraseBackground=False)`.  The `__refreshing` flag is set
during Freeze/Thaw to suppress selection events, then cleared
immediately after Thaw.  No paint suppression, no idle wait.

**2. EventFilter motion blocking** (`frame.py`):
`_RebuildInputFilter` is a `wx.EventFilter` that silently eats mouse
**motion** events (MOTION, ENTER_WINDOW, LEAVE_WINDOW) at the wx level.
Clicks, keyboard, and scroll events pass through normally so the app
stays responsive.  Only motion events are suppressed because they drive
the AUI cascade (OnMotion -> hover state change -> repaint -> repeat).
Each `_do_full_rebuild` call increments a refcount via `acquire()` and
decrements via `release()`.  When the last widget completes, a
1-second deferred release timer starts to cover the post-rebuild
settling period.  If a new rebuild starts during the settling, the
timer is cancelled and the filter stays active.

### How the layers work together

```
RefreshAllItems()
    ├── snapshot comparison: tree unchanged? -> refresh in place, return
    ├── _input_filter.acquire()  (refcount++, filter active)
    ├── __refreshing = True  (selection events suppressed)
    ├── Freeze -> delete -> rebuild -> Thaw
    ├── __refreshing = False
    ├── restore selection, scroll
    ├── Refresh(eraseBackground=False)  (immediate paint)
    ├── _input_filter.release()  (refcount--, deferred release if 0)
    └── 1s later: filter deactivates (motion events resume)
```

The rebuild is synchronous - no blank screen, no idle wait.  The
motion filter prevents the AUI cascade that was the original problem.

**History:** v2.0.2.6-v2.0.2.8 used paint suppression (intercepting
OnPaint with empty PaintDC during `__refreshing`) and an idle wait
(2-3 EVT_IDLE cycles to clear `__refreshing`).  This caused the tree
to go blank for 50-200ms per rebuild.  Removed in v2.0.2.10 because
the motion-only input filter is sufficient to prevent the cascade.

### What was tried and abandoned

| # | Approach | Result |
|---|----------|--------|
| 1 | `Freeze` main frame during rebuild | `Thaw()` burst: 3→25 expose events |
| 2 | `wx.CallAfter` deferral | Cascade occurs before command runs |
| 3 | `Unbind`/`Bind` `OnPaint` with DC clipping | No impact — GDK damage is below DC layer |
| 4 | Instance-level `Repaint` override | Not reached (bound method capture) |
| 5 | Class-level `Repaint` debounce (50ms throttle) | Suppressed ~half, but AUI still cascades |
| 6 | `wx.WindowDisabler` | Grays out menu bar on GTK3 (calls `gtk_widget_set_sensitive`) |
| 7 | Always-on paint throttle (1 per 100ms + deferred `Refresh()`) | Ghosting and missing paints everywhere — suppressed paints with empty `PaintDC` leave stale content, deferred `Refresh()` doesn't reliably produce a clean repaint. A guard on repaint does not work because it creates a lot of ghosting/missing-paint problems |
| 8 | `RefreshAllItems` time-based throttle (skip if <100ms, schedule `CallLater(100, RefreshAllItems)`) | Deferred calls triggered full 80ms rebuilds when only a repaint was needed; cascade of deferred calls from multiple widgets |
| 9 | Remove `__refreshing` re-entry guard entirely | Empty lists on startup — legitimate refresh calls during 703ms idle wait were no longer blocked, but without `__refreshing` flag the paint debounce and selection suppression also stopped working |
| 10 | Paint throttle 1-per-100ms during `__refreshing` | Each cascade paint takes ~280ms (291 items), so paints are always >100ms apart — throttle never triggers. Cascade runs unimpeded. Only total suppression (zero paints during refresh) breaks the cycle |
| 11 | Per-widget EventFilter release (each `_on_refresh_idle` sets `active=False`) | First widget to finish clears the filter while other widgets still need it. Global singleton filter requires refcount + deferred release |
| 12 | `__refreshing` as re-entry guard for `RefreshAllItems` | Blocks legitimate refresh calls for 703ms during idle wait, causing empty lists on startup. Removed re-entry guard - `__refreshing` now only drives paint suppression and selection suppression |
| 13 | EventFilter eating ALL input (clicks, keyboard, scroll, motion) | Clicks and keyboard events lost during rebuild + 1s settling period makes the app feel unresponsive. Only motion events drive the AUI cascade; clicks and keyboard do not. Narrowed filter to motion events only |
| 14 | Paint suppression (empty PaintDC during `__refreshing`) + idle wait (2-3 EVT_IDLE cycles) | Tree goes blank for 50-200ms per rebuild because ALL paints are suppressed until idle completes. Multiple rebuilds (filter + sort + presentation) stack the blank time to seconds. The motion-only input filter is sufficient to prevent the AUI cascade without paint suppression |

### Resolved Questions

1. **"Non-deterministic" cascade** — Determined by mouse position.
   Mouse over list area = cascade; mouse on toolbar = fast.

2. **Instance Repaint override not reached** — `self.Bind()` captures
   bound method at bind time.  Class-level `Repaint` IS reached
   (`self.Repaint()` does runtime class lookup), but class-level
   `OnPaint` is NOT.

3. **DC clipping** — Does NOT prevent GTK3 damage.  GdkWindow damage
   propagation operates below the wx DC layer.

4. **wx.WindowDisabler** — Works at native GDK level (blocks all input)
   but calls `gtk_widget_set_sensitive(FALSE)` which grays out the
   menu bar.  Replaced by `wx.EventFilter` which operates at wx level
   without visual effects.

5. **AUI Repaint debounce** — Suppressed some repaints but the cascade
   still ran through paint events.  Replaced by total paint suppression
   on the tree widget's OnPaint which breaks the cascade at its source.

6. **Cascade is self-sustaining without mouse input** — Even with all
   mouse events eaten by the EventFilter, the cascade continues: AUI
   paint → GDK damage → child repaint → AUI repaint → repeat.  Each
   tree paint of 291 items takes ~280ms.  Mouse events make it worse
   but are not required.  Total paint suppression during `__refreshing`
   is the only effective fix.

7. **EventFilter cannot catch events during synchronous processing** —
   During a long paint handler (~280ms), the wx event loop doesn't run,
   so `FilterEvent` never fires.  Motion events queue in GTK and are
   only dispatched between paints.  With total paint suppression, the
   event loop runs freely and the filter catches all motion events.

### Open Questions

1. **Is the cascade specific to `agw.aui`?**  Would the cascade also
   occur with standard `wx.aui.AuiManager` (C++ implementation) or
   is it specific to the pure-Python `agw` version?

2. **Full rebuild on every editor field change** - Editing any field
   in the task or category editor (even subject, notes, colors) triggers
   a full `RefreshAllItems` rebuild of every tree view.  The tree is not
   virtual - each rebuild deletes all nodes and recreates them (text,
   colors, fonts, images for every item and column).  For 291 items
   with 8 columns this is ~2300 text lookups + 291 color/font
   computations + a 280ms paint.

   The tree already has per-item `RefreshItems()` that updates just the
   changed rows in place (text, colors, font, repaint line).  The
   filter's `reset()` and sorter's `reset()` both check whether the
   result actually changed before firing events.  But something in the
   event chain still triggers a full rebuild on every edit.  Need caller
   tracing to identify the exact path.

   User request: "Why every time that I change a value in the edit task
   window, all lists in my views flicker, seems like they are being
   fully rebuilt" and "same thing for each time I edit values of a
   category" and "Any fields, even a task or category subject."

   Ideal fix: attribute changes that don't affect sort order or filter
   membership should use per-item `RefreshItems()` only, never a full
   `RefreshAllItems()` rebuild.  The list control (`wx.LC_VIRTUAL`) is
   already virtual and cheap to refresh.  The tree control
   (`HyperTreeList`) is not virtual and cannot reorder nodes in place -
   it has no `MoveItem()` API - so sort order changes do require a full
   rebuild, but non-sort attribute changes should not.

### Key Files

| File | Role |
|------|------|
| `taskcoachlib/widgets/treectrl.py` | `RefreshAllItems()`, snapshot comparison, synchronous rebuild |
| `taskcoachlib/widgets/frame.py` | `_RebuildInputFilter` (motion-only EventFilter with refcount + deferred release), sash throttle |
| `taskcoachlib/gui/viewer/base.py` | `refresh()` - calls `RefreshAllItems` |
| `taskcoachlib/meta/debug.py` | `log_step()` - timestamped debug logging |

---

## Key Files

| File | Purpose |
|------|---------|
| `taskcoachlib/gui/viewer/base.py` | Base viewer with `curselection()`, `onSelect()`, `onPresentationChanged()` |
| `taskcoachlib/gui/viewer/task.py` | `CalendarViewer.reconfig()` |
| `taskcoachlib/gui/status.py` | Status bar with 500ms debounce |
| `taskcoachlib/widgets/treectrl.py` | Tree widget: selection, scroll, hover, synchronous rebuild |
| `taskcoachlib/widgets/listctrl.py` | List widget with selection handling |
| `taskcoachlib/widgets/iconpicker.py` | Icon picker: virtual ListCtrl (`wx.LC_VIRTUAL`) for fast population |
| `taskcoachlib/widgets/tooltip.py` | Tooltip mixin with deferred data prep |
| `taskcoachlib/widgets/frame.py` | AUI frame, `_RebuildInputFilter` (EventFilter), sash throttle |
| `taskcoachlib/patches/hypertreelist.py` | Patched upstream widget — hover outline, drag highlight |

