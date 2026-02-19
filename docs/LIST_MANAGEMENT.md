# List Management Architecture

## Table of Contents

1. [TODO](#todo)
2. [Overview](#overview)
3. [Selection SSOT Principle](#selection-ssot-principle)
4. [Multi-Window Architecture](#multi-window-architecture)
5. [Select Next After Deletion](#select-next-after-deletion)
6. [Status Bar Updates](#status-bar-updates)
7. [Scroll After Rebuild (Tree Views)](#scroll-after-rebuild-tree-views)
8. [Row Hover Outline](#row-hover-outline)
9. [Mouse-Move Handler Inventory (Tree Views)](#mouse-move-handler-inventory-tree-views)
10. [Vampire CPU Usage](#vampire-cpu-usage)
11. [AUI Sash Resize Throttle](#aui-sash-resize-throttle)
12. [Key Files](#key-files)

---

## TODO

1. **Selection highlight outline:** Add the same two-tone border outline
   (currently used for hover) around the currently selected row(s) as well.
   This would provide a stronger, more accessible visual indicator for
   selection — especially on low-contrast themes or when custom row colors
   make the default selection highlight hard to see. The hover outline
   infrastructure (`_hoverItem`, `PaintLevel`, `_refreshHoverLine`) could be
   reused or extended to also draw around selected items using a different
   color pair (e.g. `SYS_COLOUR_HIGHLIGHT` / `SYS_COLOUR_HIGHLIGHTTEXT`).
2. **Eliminate UpdateUI polling entirely:** See [Vampire CPU Usage](#vampire-cpu-usage)
   for Option A (all buttons always enabled) and Option B (event-driven updates).

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

## Scroll After Rebuild (Tree Views)

### Problem

After filter changes, search clears, or category toggles, the selected item scrolls off-screen in tree views. The user must press arrow keys to find it.

### Root Cause

HyperTreeList's `ScrollTo()` (upstream, in `hypertreelist.py`) calls `CalculatePositions()` when `_dirty` but never calls `AdjustMyScrollbars()`. During normal use (click, keyboard), scrollbars are already current. But after a freeze/thaw rebuild cycle (`RefreshAllItems` in `treectrl.py`), the scrollbar range is stale. `Scroll()` gets clamped to the old range and silently does nothing.

This is an upstream design limitation (same in wxPython 4.2.0 and current master), not a bug in our code.

**Does NOT affect list views** — `VirtualListCtrl` uses native wx scrollbar management.

### Fix: Two Scroll Methods

Both methods live on the tree control subclass in `treectrl.py`. Both call `AdjustMyScrollbars()` before scrolling to fix the stale range.

**`scrollToSelection()`** — Minimal scroll to make first selected item visible.
- Called from: `treectrl.py:RefreshAllItems()` — fires for ALL callers (init, file load, expand/collapse, sort, etc.)
- Reference: `treectrl.py:TreeListCtrl.scrollToSelection`

**`scrollToSelectionCentered()`** — Centers viewport on first selected item.
- Called from: `base.py:onPresentationChanged()` — fires only on add/remove events (filter toggle, search, category filter), batched by `@eventSource`
- Overrides the position set by `scrollToSelection()` in the same flow
- Reference: `treectrl.py:TreeListCtrl.scrollToSelectionCentered`

### Flow

**Filter toggle / search / category filter / add / delete** — fires add/remove events:
```
onPresentationChanged (base.py)
  → refresh()
    → widget.RefreshAllItems() (treectrl.py)
      → Freeze → DeleteAll → Add → Thaw → restore selection
      → scrollToSelection()                    ← ensure-visible
  → scrollToSelectionCentered()                ← center on selected
```

**Mode switch (list ↔ tree)** — fires sort event, NOT add/remove:
```
onTreeListModeChanged (task.py)
  → presentation().setTreeMode(value)
    → Sorter.reset() → fires sortEventType (NOT add/remove)
      → onSortOrderChanged (mixin.py) → refresh()
        → widget.RefreshAllItems()
          → scrollToSelection()              ← ensure-visible
  → scrollToSelectionCentered()              ← center on selected (explicit)
```
Note: `Sorter.reset()` fires `pub.sendMessage(self.sortEventType())`, not add/remove
events, so `onPresentationChanged` does NOT fire. The centering call is explicit in
`onTreeListModeChanged`.

### Scroll Behavior by User Action

All tree-based viewers (task tree, category tree, note tree) follow this table.
List-only viewers (effort, attachments) always use `ensureSelectionVisible` (native wx).

| User Action                     | Scroll Behavior | Path                                     |
|---------------------------------|-----------------|------------------------------------------|
| Toggle status filter            | Center          | `onPresentationChanged` → centered       |
| Toggle category filter          | Center          | `onPresentationChanged` → centered       |
| Clear/change search text        | Center          | `onPresentationChanged` → centered       |
| Switch list ↔ tree mode         | Center          | `onTreeListModeChanged` → explicit centered |
| Delete selected item            | Center          | `onPresentationChanged` → centered       |
| Add new item                    | Center          | `onPresentationChanged` → centered       |
| Window resize                   | Center          | `EVT_SIZE` → `CallAfter` → centered     |
| Sort change                     | Ensure-visible  | `refresh()` only, no `onPresentationChanged` |
| Expand all / Collapse all       | Ensure-visible  | `refresh()` only, no `onPresentationChanged` |
| Item edit (attribute change)    | No scroll       | `RefreshItems()`, not `RefreshAllItems`  |
| File load                       | Ensure-visible  | `onEndIO` → `refresh()` only             |
| Initial startup                 | Ensure-visible  | `__init__` → `refresh()` only            |

**Center** = `scrollToSelectionCentered()` — viewport centers on first selected item
**Ensure-visible** = `scrollToSelection()` — minimal scroll, just makes item visible
**No scroll** = individual rows refreshed in place, no scroll change

---

## Row Hover Outline

A two-tone (fg/bg) hover outline on all list and tree view rows, following the
W3C WCAG C40 technique used by Chrome/Edge focus indicators. An inner line uses
`SYS_COLOUR_WINDOWTEXT` and an outer line uses `SYS_COLOUR_WINDOW`, guaranteeing
visibility on any background including selected, custom-colored, and unfocused
rows. Line thickness is configurable via **Preferences > Theme > Hoverover
Highlight** (default 1, 0 to disable). The setting is re-read on each row
change, so changes take effect immediately without restart.

The expensive `OnBeforeShowToolTip()` call (HitTest + full tooltip data
extraction traversing notes, categories, attachments, descriptions) is deferred
from every mouse-move event to a 200ms timer callback. Only the mouse position
is stored on motion; data extraction runs once after the cursor is still.

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
    │           ├── _readHoverSetting()            ← re-read config
    │           ├── _refreshHoverLine(prevItem)     ← erase old outline
    │           └── _refreshHoverLine(newItem)      ← trigger repaint
    │
    └── event.Skip() → tooltip __OnMotion also fires
```

**State:** `TreeListMainWindow._hoverItem` — the currently hovered item, or `None`.

**Drawing:** In `PaintLevel()` in `hypertreelist.py`, after row lines and before
DC restore. Draws outer 1px bg rect (inflated by 1), then inner 1px fg rect.
Skipped for drag items.

**Cleanup:** `EVT_LEAVE_WINDOW` → `SetHoverItem(None)`.

**Ghosting prevention:** `_refreshHoverLine()` inflates the invalidation rect by
3px (1px inner + 1px outer + safety) so the full two-tone outline is erased on
repaint.

### List Views (VirtualListCtrl)

```
EVT_MOTION on VirtualListCtrl
    │
    ├── _onHoverMotion()
    │   └── HitTest → update _hover_row
    │       ├── _refreshHoverRow(old)   ← padded RefreshRect
    │       └── _refreshHoverRow(new)   ← padded RefreshRect
    │       └── CallAfter(_drawHoverOutline)
    │
    └── event.Skip()
```

Native `wx.ListCtrl` has no PaintItem hook, so the outline is drawn post-paint
via `wx.ClientDC` + `wx.CallAfter`. `EVT_PAINT` also triggers a deferred redraw
to survive native repaints.

**Cleanup:** `EVT_LEAVE_WINDOW` → reset `_hover_row`, padded refresh.

### Settings

`hoverlinewidth` in `[window]` — integer, default 1. 0 disables hover, >0
enables the two-tone outline. User-facing path: **Preferences > Theme >
Hoverover Highlight**. Read into a local cache at init, on
`RefreshAllItems()`, and re-read on each row change via `_readHoverSetting()`.

---

## Mouse-Move Handler Inventory (Tree Views)

Only two handlers fire on mouse motion. Both call `event.Skip()` so the chain is not broken.

| Handler | File | Purpose |
|---------|------|---------|
| `OnMouse` fast-path | `hypertreelist.py` | Row-bounds cache → HitTest only on row change → update `_hoverItem` |
| `__OnMotion` (ToolTipMixin) | `tooltip.py` | Store position, start 200ms timer |
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

**Removed:** `_onHoverMotion` (was in `treectrl.py`) — performed a duplicate
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

So for Edit, Delete, TaskMarkInactive, TaskMarkActive, TaskMarkCompleted,
NewSubItem, and others, every 200ms wx:

1. Calls `widget.curselection()` → iterates all selected tree items → maps
   each to a domain object via `GetItemPyData()`
2. Some also call `curselectionIsInstanceOf()` → iterates again with
   `isinstance()` checks on every selected item

All to answer "should this button be greyed out?" — when nothing has changed.
This is pure waste. The correct approach would be event-driven: update button
states only when selection or data actually changes, not by continuous polling.

### TODO: Eliminate UpdateUI polling entirely

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
enabled and make `doCommand()` no-op when the action doesn't apply (no
selection, wrong item type, etc.). This eliminates the entire UpdateUI
mechanism — no polling, no `enabled()` calls, no `EVT_UPDATE_UI` bindings,
zero idle CPU. The greyed-out visual is a minor UX hint that doesn't justify
continuous CPU polling. Clicking "Delete" with nothing selected simply does
nothing. This is how many modern apps work (e.g. VS Code toolbar buttons
don't grey out). The `doCommand()` methods already guard against invalid state
in many cases via `onCommandActivate()` which checks `self.enabled(event)`.

**Recommended approach (Option A — simplest):** Make all buttons always enabled.
Remove all `EVT_UPDATE_UI` bindings from `bind()` in `base_uicommand.py`. Keep
the `enabled()` check inside `onCommandActivate()` so commands still no-op
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

## Key Files

| File | Purpose |
|------|---------|
| `taskcoachlib/gui/viewer/base.py` | Base viewer with `curselection()`, `onSelect()`, `onPresentationChanged()` |
| `taskcoachlib/gui/status.py` | Status bar with 500ms debounce |
| `taskcoachlib/widgets/treectrl.py` | Tree widget with selection handling, scroll methods, hover tracking |
| `taskcoachlib/widgets/listctrl.py` | List widget with selection handling |
| `taskcoachlib/widgets/tooltip.py` | Tooltip mixin with deferred data prep |
| `taskcoachlib/widgets/frame.py` | AUI frame with sash resize throttle |
| `taskcoachlib/patches/hypertreelist.py` | Patched upstream widget — hover outline, drag highlight |

