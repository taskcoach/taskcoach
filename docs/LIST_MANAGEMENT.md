# List Management Architecture

## Table of Contents

1. [Overview](#overview)
2. [Selection SSOT Principle](#selection-ssot-principle)
3. [Multi-Window Architecture](#multi-window-architecture)
4. [Select Next After Deletion](#select-next-after-deletion)
5. [Status Bar Updates](#status-bar-updates)
6. [Key Files](#key-files)

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

## Key Files

| File | Purpose |
|------|---------|
| `taskcoachlib/gui/viewer/base.py` | Base viewer with `curselection()`, `onSelect()`, `onPresentationChanged()` |
| `taskcoachlib/gui/status.py` | Status bar with 500ms debounce |
| `taskcoachlib/widgets/treectrl.py` | Tree widget with selection handling |
| `taskcoachlib/widgets/listctrl.py` | List widget with selection handling |

