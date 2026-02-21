# Menu Enable/Disable Architecture

## Table of Contents

1. [TODO](#todo)
2. [Design Principles](#design-principles)
3. [Architecture](#architecture)
4. [MenuItem Subclass](#menuitem-subclass)
5. [Menu State Update Flow](#menu-state-update-flow)
6. [Toolbar vs Menu Strategy](#toolbar-vs-menu-strategy)
7. [Migrated Commands](#migrated-commands)
8. [Key Files](#key-files)

---

## TODO

1. PEP 8 renames (separate commit): `appendToToolBar`, `addToMenu`, etc.
2. GTK menu width not recalculated on first open after `SetItemLabel()` changes
   text during `EVT_MENU_OPEN`. Second open sizes correctly. Affects
   `current_menu_text()` for EditUndo/EditRedo and EditPasteAsSubItem.

---

## Design Principles

> The menu item knows if it should be enabled, it relies on menu class
> level methods to modularize. The menu iterates through all items,
> telling them to set_enabled.

- **Separation of concern**: Each menu item is an encapsulated object
  that manages its own enabled state.
- **No polling**: The old system polled ~30 buttons every 200ms via
  `EVT_UPDATE_UI`. The new system updates on demand (menu open, signals).
- **Dependency injection**: Each `MenuItem` receives its `UICommand` at
  creation. The item only depends on the `enabled()` interface.
- **Menu as orchestrator**: The menu iterates its items and tells each
  to update. It does not compute enabled state itself.
- **Command owns its check**: Each command's `enabled()` is the SSOT for
  that command's enabled state. It queries its own references (`self.viewer`,
  `self.iocontroller`, `self.taskList`, etc.) directly. No intermediary.

---

## Architecture

```
Menu open event
    └── MainMenu._on_menu_open(event)          [EVT_MENU_OPEN]
        └── menu._update_menu_state()
            └── for each MenuItem:
                └── item.update_enabled_state()
                    └── item.Enable(item._command.enabled())
                        └── command determines its own state
```

For popup (context) menus:
```
Right-click
    └── _updateMenuUI()
        └── popup_menu._update_menu_state()
            └── (same per-item flow as above)
```

---

## MenuItem Subclass

`MenuItem(wx.MenuItem)` in `base_uicommand.py` — each item receives its
`UICommand` at creation (dependency injection) and owns its enabled state
via `update_enabled_state()`. Created in `UICommand.addToMenu()`.

---

## Menu State Update Flow

- **Main menus**: `EVT_MENU_OPEN` → `MainMenu._on_menu_open()` →
  `menu._update_menu_state()` → each item's `update_enabled_state()`.
  Fires per menu/submenu on GTK.
- **Popup menus**: `_updateMenuUI()` in `itemctrl.py` →
  `popup._update_menu_state()` → same per-item flow.

---

## Toolbar vs Menu Strategy

| Concern     | Toolbar buttons              | Menu items                    |
|-------------|------------------------------|-------------------------------|
| **Trigger** | Publisher signals (per-instance) | Menu open event            |
| **Pattern** | `_ViewSettingsSync`, `_SelectionSync` | `_update_menu_state()` |
| **Polling** | None — signal-driven         | None — on-demand on open      |
| **Update**  | `toolbar.EnableTool(id, bool)` | `menuItem.update_enabled_state()` |

Toolbar buttons use Publisher/Observer signals because they're always
visible and must update immediately on state change. Menu items only
need to be correct when visible (on open).

Toolbar **dropdowns** (`ToolbarChoiceCommandMixin`) also use
`view_settings_changed_event_type()`. On signal, they read current
state from the viewer (`viewer.aggregation`, `viewer.order_by`, etc.)
and call `setChoice()`. Their `doChoice()` calls the viewer entry
point (e.g., `viewer.set_aggregation()`).

See [LIST_MANAGEMENT.md](LIST_MANAGEMENT.md) for toolbar signal details
(Selection-Driven Button Enable/Disable, Tree Mode Button Enable/Disable).

---

## Migrated Commands

### ViewExpandAll / ViewCollapseAll

- No `EVT_UPDATE_UI` polling
- `enabled()`: command determines its own state (tree mode required)
- Toolbar: signal-driven via `_ViewSettingsSync`
- Menu: updated via `_update_menu_state()` on menu open

### EditCut / EditCopy / ClearSelection / Edit / Delete / Mail

- No `EVT_UPDATE_UI` polling
- `enabled()`: command determines its own state (selection required)
- Toolbar: signal-driven via `_SelectionSync`
- Menu: updated via `_update_menu_state()` on menu open

### TaskMarkActive / TaskMarkInactive / TaskMarkCompleted

- No `EVT_UPDATE_UI` polling
- `enabled()`: command determines its own state (selection + task state)
- Toolbar: signal-driven via `_SelectionSync`
- Menu: updated via `_update_menu_state()` on menu open

### EffortStart / EffortStartForEffort

- No `EVT_UPDATE_UI` polling
- `enabled()`: command determines its own state (selection + type + trackability)
- Toolbar: signal-driven via `_SelectionSync`
- Menu: updated via `_update_menu_state()` on menu open

### EffortNew

- No `EVT_UPDATE_UI` polling
- `enabled()`: task list non-empty; in task viewer also requires selection
- Toolbar: signal-driven via `_SelectionSync` (guarded — no viewer in tray menu)
- Menu: updated via `_update_menu_state()` on menu open

### EditPasteAsSubItem

- No `EVT_UPDATE_UI` polling
- `enabled()`: selection + clipboard non-empty + type compatibility
- Menu-only (no toolbar) — updated via `_update_menu_state()` on menu open
- `current_menu_text()`: dynamically returns "Paste as subtask/subnote/subcategory"

### ResetFilter

- No `EVT_UPDATE_UI` polling
- `enabled()`: command determines its own state (`viewer.has_filter()`)
- Toolbar: signal-driven via `Filter.filter_change_event_type()` (fires on any filter change)
- Menu: updated via `_update_menu_state()` on menu open

### SelectAll

- No `EVT_UPDATE_UI` polling
- `enabled()`: always True
- Menu-only (no toolbar) — updated via `_update_menu_state()` on menu open

### ToggleCategory

- No `EVT_UPDATE_UI` polling
- `enabled()`: selection + categorizable type + mutual exclusive ancestor check
- `checked()`: whether all selected items have this category
- Menu-only (no toolbar) — updated via `_update_menu_state()` on menu open

### FileSave

- No `EVT_UPDATE_UI` polling
- `enabled()`: `iocontroller.need_save()`
- Toolbar: signal-driven via `taskfile.dirty` / `taskfile.clean` pubsub
- Menu: updated via `_update_menu_state()` on menu open

### FileMergeDiskChanges

- No `EVT_UPDATE_UI` polling
- `enabled()`: `iocontroller.changed_on_disk()`
- Toolbar: signal-driven via `taskfile.changed` / `taskfile.dirty` / `taskfile.clean` pubsub
- Menu: updated via `_update_menu_state()` on menu open

### FilePurgeDeletedItems

- No `EVT_UPDATE_UI` polling
- `enabled()`: `iocontroller.has_deleted_items()`
- Menu-only (no toolbar) — updated via `_update_menu_state()` on menu open

### ViewerHideTasks (task status filter buttons)

- No `EVT_UPDATE_UI` polling
- `enabled()`: always True (filter buttons are always enabled)
- `checked()`: via `BooleanSettingsCommand.checked()` → `viewer.is_hiding_task_status()`
- Toolbar: signal-driven via `Filter.filter_change_event_type()` → `ToggleTool(checked())`
- Menu: updated via `_update_menu_state()` on menu open

### ViewerHideCompositeTasks

- No `EVT_UPDATE_UI` polling
- `enabled()`: `not viewer.is_tree_viewer()` (list mode only)
- `checked()`: via `BooleanSettingsCommand.checked()`
- Menu-only (no toolbar) — updated via `_update_menu_state()` on menu open

### EditTrackedTasks

- No `EVT_UPDATE_UI` polling
- `enabled()`: `any(taskList.tasks_being_tracked())`
- Menu-only (no toolbar) — updated via `_update_menu_state()` on menu open

### EditUndo / EditRedo

- No `EVT_UPDATE_UI` polling
- `enabled()`: command determines its own state (CommandHistory or focused TextCtrl)
- `current_menu_text()`: dynamic text ("Undo *add task*", "Redo *delete*")
- Toolbar: signal-driven via `commandhistory.changed` pubsub
- Menu: updated via `_update_menu_state()` on menu open

### TaskPriorityParentMenu (parent menu item with submenu)

- `enabled()`: `viewer.has_selection and viewer.is_task`
- `doCommand()`: no-op (clicking opens the submenu, not a command action)
- `addToMenu()` called with `subMenu=TaskPriorityMenu(...)` — creates a
  `MenuItem` that is both a submenu header and a command-backed item
- `_update_menu_state()` picks it up like any other `MenuItem` via
  `update_state()` — no special submenu handling needed
- This is the pattern for parent menu items that need enable/disable:
  create a UICommand with `enabled()` and pass the submenu via
  `addToMenu(menu, window, subMenu=...)`. The command owns the text,
  icon, and enabled logic. The menu just calls `addToMenu()`.

### EffortViewerAggregationChoice / EffortViewerAggregationOption

- Toolbar dropdown (`EffortViewerAggregationChoice`): signal-driven via
  `view_settings_changed_event_type()`, reads `viewer.aggregation`
- Menu radio (`EffortViewerAggregationOption`): `isSettingChecked()` reads
  `viewer.aggregation`, `doCommand()` calls `viewer.set_aggregation()`
- Entry point: `EffortViewer.set_aggregation()` — writes settings, refreshes,
  fires signal

### SquareTaskViewerOrderChoice / SquareTaskViewerOrderByOption

- Toolbar dropdown (`SquareTaskViewerOrderChoice`): signal-driven via
  `view_settings_changed_event_type()`, reads `viewer.order_by`
- Menu radio (`SquareTaskViewerOrderByOption`): `isSettingChecked()` reads
  `viewer.order_by`, `doCommand()` calls `viewer.set_order_by()`
- Entry point: `SquareTaskViewer.set_order_by()` — writes settings, applies
  change, fires signal

---

## Key Files

| File | Role |
|------|------|
| `taskcoachlib/gui/uicommand/base_uicommand.py` | `MenuItem` subclass, `UICommand` base with `addToMenu()` |
| `taskcoachlib/gui/uicommand/uicommand.py` | Concrete commands with `enabled()` overrides |
| `taskcoachlib/gui/uicommand/mixin_uicommand.py` | `PopupButtonMixin` (toolbar popup menu behavior) |
| `taskcoachlib/gui/menu.py` | `Menu._update_menu_state()`, `MainMenu._on_menu_open()` |
| `taskcoachlib/gui/viewer/base.py` | `has_selection` property, `is_tree_viewer()`, selection signals |
| `taskcoachlib/widgets/itemctrl.py` | `_updateMenuUI()` for popup menus |
