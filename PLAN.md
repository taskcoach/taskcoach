# Cross-Viewer Drag-and-Drop Implementation Plan

## Goal
Enable dragging task(s) onto categories to assign them, and dragging category(ies) onto tasks to assign those categories.

## Current Architecture

### Existing DnD Flow
1. `TreeCtrlDragAndDropMixin` handles tree-internal drag via `EVT_TREE_BEGIN_DRAG`/`EVT_TREE_END_DRAG`
2. `_dragItems` stores tree items being dragged (instance variable, not shared)
3. `DropTarget` class handles external drops (files, URLs, mail) via `wx.DropTarget`
4. Each viewer has its own `OnDrop()` that only handles same-type items

### Key Files
- `taskcoachlib/widgets/draganddrop.py` - Core DnD mixin and DropTarget
- `taskcoachlib/widgets/treectrl.py` - TreeListCtrl with DnD support
- `taskcoachlib/gui/viewer/task.py` - Task viewer
- `taskcoachlib/gui/viewer/category.py` - Category viewer
- `taskcoachlib/command/categorizableCommands.py` - ToggleCategoryCommand

## Implementation Approach

### Option A: Extend wx.DropTarget with Custom Data Object
- Create `TaskCoachItemsDataObject` with custom format `"application/x-taskcoach-items"`
- Modify `StartDragging()` to use `wx.DropSource.DoDragDrop()`
- Each viewer's DropTarget checks data type and handles appropriately

### Option B: Global Drag State (Simpler)
- Add module-level `_currentDragSource` and `_currentDragItems` in draganddrop.py
- When drag starts, store the source viewer and items
- When drop occurs on any viewer, check if items are compatible
- Clear state when drag ends

**Recommendation**: Option B is simpler and sufficient since we're within the same application.

## Detailed Steps

### Step 1: Add Global Drag State (`draganddrop.py`)
```python
# Module-level drag state for cross-viewer drops
_currentDragSource = None  # The viewer/tree that started the drag
_currentDragItems = []     # Domain objects being dragged

def getCurrentDragInfo():
    return _currentDragSource, _currentDragItems

def setCurrentDragInfo(source, items):
    global _currentDragSource, _currentDragItems
    _currentDragSource = source
    _currentDragItems = items

def clearCurrentDragInfo():
    global _currentDragSource, _currentDragItems
    _currentDragSource = None
    _currentDragItems = []
```

### Step 2: Modify TreeCtrlDragAndDropMixin (`draganddrop.py`)
- In `OnBeginDrag()`: Call `setCurrentDragInfo()` with domain objects
- In `StopDragging()`: Call `clearCurrentDragInfo()`

### Step 3: Extend DropTarget for Internal Items (`draganddrop.py`)
- Add custom data format to composite data object
- Add `onDropItemsCallback` parameter
- In `OnData()`, check for internal items format

### Step 4: Handle Task Drop on Category (`category.py`)
- In `widgetCreationKeywordArguments()`, add `onDropItems` callback
- Implement `onDropItems()` to assign dropped tasks to target category
- Use existing `ToggleCategoryCommand`

### Step 5: Handle Category Drop on Task (`task.py`)
- Similar to Step 4, but assigns categories to the target task

### Step 6: Cursor Feedback
- Modify `OnDragging()` to check if over a compatible viewer
- Show hand cursor if drop is valid, X cursor if not

## Commands to Use

### Assigning category to task(s)
```python
from taskcoachlib.command import categorizableCommands
cmd = categorizableCommands.ToggleCategoryCommand(
    items=tasks,        # tasks to modify
    category=category   # category to assign
)
cmd.do()
```

## Testing Scenarios
1. Drag single task → drop on category → task should have category assigned
2. Drag multiple tasks → drop on category → all tasks should have category
3. Drag single category → drop on task → task should have category assigned
4. Drag multiple categories → drop on task → task should have all categories
5. Drag task → drop on same task viewer (no category) → should work as before
6. Drag task → hover over category viewer → hand cursor
7. Drag task → hover over invalid area → X cursor
8. Cancel drag (Escape/release outside) → no changes

## Files to Modify
1. `taskcoachlib/widgets/draganddrop.py` - Add global state, extend DropTarget
2. `taskcoachlib/widgets/treectrl.py` - Set drag info on begin drag
3. `taskcoachlib/gui/viewer/category.py` - Handle task drops
4. `taskcoachlib/gui/viewer/task.py` - Handle category drops
5. `taskcoachlib/meta/data.py` - Version bump
