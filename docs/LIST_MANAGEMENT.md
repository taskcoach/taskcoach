# List Management Architecture

## Table of Contents

1. [Overview](#overview)
2. [Selection SSOT Principle](#selection-ssot-principle)
3. [Multi-Window Architecture](#multi-window-architecture)
4. [Select Next After Deletion](#select-next-after-deletion)
5. [Status Bar Updates](#status-bar-updates)
6. [Scroll After Rebuild (Tree Views)](#scroll-after-rebuild-tree-views)
7. [Key Files](#key-files)

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

## Key Files

| File | Purpose |
|------|---------|
| `taskcoachlib/gui/viewer/base.py` | Base viewer with `curselection()`, `onSelect()`, `onPresentationChanged()` |
| `taskcoachlib/gui/status.py` | Status bar with 500ms debounce |
| `taskcoachlib/widgets/treectrl.py` | Tree widget with selection handling, scroll methods |
| `taskcoachlib/widgets/listctrl.py` | List widget with selection handling |
| `taskcoachlib/patches/hypertreelist.py` | Patched upstream widget — DO NOT MODIFY (see `CRITICAL_WXPYTHON_PATCH.md`) |

