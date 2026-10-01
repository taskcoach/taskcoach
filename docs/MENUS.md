# Menu Enable/Disable Architecture

## Table of Contents

1. [TODO](#todo)
2. [Design Principles](#design-principles)
3. [Architecture](#architecture)
4. [MenuItem Subclass](#menuitem-subclass)
5. [Menu State Update Flow](#menu-state-update-flow)
6. [Toolbar vs Menu Strategy](#toolbar-vs-menu-strategy)
7. [Migrated Commands](#migrated-commands)
8. [Keyboard Shortcuts](#keyboard-shortcuts)
9. [Key Files](#key-files)

---

## TODO

1. ~~PEP 8 renames (separate commit): `append_to_toolbar`, `add_to_menu`, etc.~~ — **DONE.** All UICommand methods and constructor kwargs renamed to snake_case.
2. ~~GTK menu width not recalculated on first open after `SetItemLabel()` changes
   text during `EVT_MENU_OPEN`. Second open sizes correctly.~~ — **Partially fixed.**
   EditUndo/EditRedo now update labels proactively via Publisher event from
   `CommandHistory`; `current_menu_text()` returns `None` so `SetItemLabel` is
   skipped during `EVT_MENU_OPEN`. **Remaining:** EditPasteAsSubItem still
   changes label during `EVT_MENU_OPEN`.
   See [PUBLISHER_OBSERVER.md — GTK3 Dynamic Menu Item Sizing](PUBLISHER_OBSERVER.md#gtk3-dynamic-menu-item-sizing)
   for the full pattern.

---

## Design Principles

> The menu item knows if it should be enabled, it relies on menu class
> level methods to modularize. The menu iterates through all items,
> telling them to set_enabled.

- **Separation of concern**: Each menu item's command owns its enabled
  state, check mark and label.
- **No polling**: Toolbar buttons follow signals. Menu items answer wx's
  `EVT_UPDATE_UI`, which wx sends only when a menu opens, before a popup
  menu shows and before an item's shortcut acts. Update events in idle
  time are off (`wx.UpdateUIEvent.SetUpdateInterval(-1)`), and the
  toolbar skips AGW's own idle loop over its tools
  (`_Toolbar.DoIdleUpdate()`).
- **Dependency injection**: Each `MenuItem` receives its `UICommand` at
  creation. The item only depends on the `enabled()` interface.
- **Menu as orchestrator**: The menu (`wx.Menu.UpdateUI()`) iterates its
  items and submenus and asks each command. It does not compute enabled
  state itself.
- **Command owns its check**: Each command's `enabled()` is the SSOT for
  that command's enabled state. It queries its own references (`self.viewer`,
  `self.iocontroller`, `self.taskList`, etc.) directly. No intermediary.

---

## Architecture

```
A menu opens, a popup menu shows, or an item's shortcut is pressed
    └── wx: menu.UpdateUI()
        └── EVT_UPDATE_UI for each item, submenus included
            └── UICommand.on_menu_update_ui(event)
                └── event.Enable(enabled()), Check(checked()),
                    SetText(current_menu_text())
```

Every platform asks for an item's state just before its shortcut acts,
and wx turns that into the same update events: GTK's can-activate-accel
signal, Windows' `WM_INITMENUPOPUP` (sent for an accelerator as for a
menu opening), macOS's item validation. All three skip a disabled
item's shortcut, so without these answers an item disabled when its
menu last opened blocked its shortcut until the menu opened again
(P130 in [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md)).

---

## MenuItem Subclass

`MenuItem(wx.MenuItem)` in `base_uicommand.py` keeps the `UICommand` it
was created with (`UICommand.add_to_menu()`). `add_to_menu()` binds the
command's `on_menu_update_ui()` for the item's id, for menu items only,
never toolbar buttons; `remove_from_menu()` and `Menu.DestroyItem()`
unbind it.

---

## Menu State Update Flow

- **Main menus**: wx's frame sends the update events when a menu opens,
  and before an item's shortcut acts.
- **Popup menus**: `PopupMenu()` sends them before showing the menu.
- **Labels** that follow data (Undo/Redo, recent files) change when the
  data changes (Publisher). Others set in `on_menu_update_ui()` change as
  the menu opens, as before; enabled and checked states change no menu
  geometry ([PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#gtk3-dynamic-menu-item-sizing)).
- **A global menu bar** (Unity-style) gets no menu-open events; with idle
  updates off its displayed states are not refreshed, as before, but
  shortcuts are still checked.

---

## Toolbar vs Menu Strategy

| Concern     | Toolbar buttons              | Menu items                    |
|-------------|------------------------------|-------------------------------|
| **Trigger** | Publisher signals (per-instance) | wx's `EVT_UPDATE_UI`: menu open, popup, shortcut |
| **Pattern** | `_ViewSettingsSync`, `_SelectionSync` | `UICommand.on_menu_update_ui()` |
| **Polling** | None: signal-driven          | None: asked on demand         |
| **Update**  | `toolbar.EnableTool(id, bool)` | `event.Enable()`, `Check()`, `SetText()` |

Toolbar buttons use Publisher/Observer signals because they're always
visible and must update immediately on state change. Menu items need to
be correct when visible and when their shortcut acts, which is when wx
asks.

Toolbar **dropdowns** (`ToolbarChoiceCommandMixin`) also use
`view_settings_changed_event_type()`. On signal, they read current
state from the viewer (`viewer.aggregation`, `viewer.order_by`, etc.)
and call `set_choice()`. Their `doChoice()` calls the viewer entry
point (e.g., `viewer.set_aggregation()`).

See [LIST_MANAGEMENT.md](LIST_MANAGEMENT.md) for toolbar signal details
(Selection-Driven Button Enable/Disable, Tree Mode Button Enable/Disable).

---

## Migrated Commands

### ViewExpandAll / ViewCollapseAll

- No `EVT_UPDATE_UI` polling
- `enabled()`: command determines its own state (tree mode required)
- Toolbar: signal-driven via `_ViewSettingsSync`
- Menu: `EVT_UPDATE_UI` (menu open, before its shortcut)

### EditCut / EditCopy / ClearSelection / Edit / Delete / Mail

- No `EVT_UPDATE_UI` polling
- `enabled()`: command determines its own state (selection required)
- Toolbar: signal-driven via `_SelectionSync`
- Menu: `EVT_UPDATE_UI` (menu open, before its shortcut)

### TaskMarkActive / TaskMarkInactive / TaskMarkCompleted

- No `EVT_UPDATE_UI` polling
- `enabled()`: command determines its own state (selection + task state)
- Toolbar: signal-driven via `_SelectionSync`
- Menu: `EVT_UPDATE_UI` (menu open, before its shortcut)

### EffortStart / EffortStartForEffort

- No `EVT_UPDATE_UI` polling
- `enabled()`: command determines its own state (selection + type + trackability)
- Toolbar: signal-driven via `_SelectionSync`
- Menu: `EVT_UPDATE_UI` (menu open, before its shortcut)

### EffortNew

- No `EVT_UPDATE_UI` polling
- `enabled()`: task list non-empty; in task viewer also requires selection
- Toolbar: signal-driven via `_SelectionSync` (guarded — no viewer in tray menu)
- Menu: `EVT_UPDATE_UI` (menu open, before its shortcut)

### EditPasteAsSubItem

- No `EVT_UPDATE_UI` polling
- `enabled()`: selection + clipboard non-empty + type compatibility
- Menu-only (no toolbar): `EVT_UPDATE_UI` (menu open, before its shortcut)
- `current_menu_text()`: dynamically returns "Paste as subtask/subnote/subcategory"

### ResetFilter

- No `EVT_UPDATE_UI` polling
- `enabled()`: command determines its own state (`viewer.has_filter()`)
- Toolbar: signal-driven via `Filter.filter_change_event_type()` (fires on any filter change)
- Menu: `EVT_UPDATE_UI` (menu open, before its shortcut)

### SelectAll

- No `EVT_UPDATE_UI` polling
- `enabled()`: always True
- Menu-only (no toolbar): `EVT_UPDATE_UI` (menu open, before its shortcut)

### ToggleCategory

- No `EVT_UPDATE_UI` polling
- `enabled()`: selection + categorizable type + mutual exclusive ancestor check
- `checked()`: whether all selected items have this category
- Menu-only (no toolbar): `EVT_UPDATE_UI` (menu open, before its shortcut)

### FileSave

- No `EVT_UPDATE_UI` polling
- `enabled()`: `iocontroller.need_save()`
- Toolbar: signal-driven via the `taskfile.dirty` / `taskfile.clean` events
- Menu: `EVT_UPDATE_UI` (menu open, before its shortcut)

### ViewerHideTasks (task status filter buttons)

- No `EVT_UPDATE_UI` polling
- `enabled()`: always True (filter buttons are always enabled)
- `checked()`: via `BooleanSettingsCommand.checked()` → `viewer.is_hiding_task_status()`
- Toolbar: signal-driven via `Filter.filter_change_event_type()` → `ToggleTool(checked())`
- Menu: `EVT_UPDATE_UI` (menu open, before its shortcut)

### ViewerHideCompositeTasks

- No `EVT_UPDATE_UI` polling
- `enabled()`: `not viewer.is_tree_viewer()` (list mode only)
- `checked()`: via `BooleanSettingsCommand.checked()`
- Menu-only (no toolbar): `EVT_UPDATE_UI` (menu open, before its shortcut)

### ToggleAutoScroll (auto-scroll to selection)

- No `EVT_UPDATE_UI` polling
- Global boolean setting `view.autoscrollselection` via `UICheckCommand`
- Toolbar: stay-pressed check button on the main toolbar and the task
  viewer toolbar; all instances sync via Publisher dispatch
  (`registerObserver`, event type `view.autoscrollselection`,
  `eventSource=settings`) -> `ToggleTool(checked())`
- Menu: View menu check item, `EVT_UPDATE_UI` on open
- See LIST_MANAGEMENT.md "Auto-Scroll Toggle" for what the setting gates

### EditTrackedTasks

- No `EVT_UPDATE_UI` polling
- `enabled()`: `any(taskList.tasks_being_tracked())`
- Menu-only (no toolbar): `EVT_UPDATE_UI` (menu open, before its shortcut)

### EditUndo / EditRedo

- No `EVT_UPDATE_UI` polling
- `enabled()`: true in a text field (it takes the key for its own undo), else the CommandHistory; the toolbar button follows the CommandHistory alone
- `current_menu_text()`: dynamic text ("Undo *add task*", "Redo *delete*")
- Toolbar: signal-driven via the `commandhistory.changed` Publisher event
- Menu: `EVT_UPDATE_UI` (menu open, before its shortcut)

### TaskPriorityParentMenu (parent menu item with submenu)

- `enabled()`: `viewer.has_selection and viewer.is_task`
- `do_command()`: no-op (clicking opens the submenu, not a command action)
- `add_to_menu()` called with `subMenu=TaskPriorityMenu(...)` — creates a
  `MenuItem` that is both a submenu header and a command-backed item
- Its `EVT_UPDATE_UI` answer serves it like any other menu item; no
  special submenu handling needed
- This is the pattern for parent menu items that need enable/disable:
  create a UICommand with `enabled()` and pass the submenu via
  `add_to_menu(menu, window, subMenu=...)`. The command owns the text,
  icon, and enabled logic. The menu just calls `add_to_menu()`.

### EffortViewerAggregationChoice / EffortViewerAggregationOption

- Toolbar dropdown (`EffortViewerAggregationChoice`): signal-driven via
  `view_settings_changed_event_type()`, reads `viewer.aggregation`
- Menu radio (`EffortViewerAggregationOption`): `is_setting_checked()` reads
  `viewer.aggregation`, `do_command()` calls `viewer.set_aggregation()`
- Entry point: `EffortViewer.set_aggregation()` — writes settings, refreshes,
  fires signal

### SquareTaskViewerOrderChoice / SquareTaskViewerOrderByOption

- Toolbar dropdown (`SquareTaskViewerOrderChoice`): signal-driven via
  `view_settings_changed_event_type()`, reads `viewer.order_by`
- Menu radio (`SquareTaskViewerOrderByOption`): `is_setting_checked()` reads
  `viewer.order_by`, `do_command()` calls `viewer.set_order_by()`
- Entry point: `SquareTaskViewer.set_order_by()` — writes settings, applies
  change, fires signal

---

## Keyboard Shortcuts

Two kinds, reaching keys in opposite order on GTK:

- **Menu shortcuts** (after `\t` in a command's menu text): the
  focused control gets the key first, the menu only what it leaves.
- **Accelerator tables** (`SetAcceleratorTable()`): wxGTK checks the
  tables of the focused window and its parents before the window
  gets the key, so a table takes its keys from every child.

A viewer's plain keys (Return, numpad Enter, Ctrl+X/C/V, Ctrl+Del)
are therefore on its list widget, not the viewer, whose toolbar holds
the search box (`Viewer.createToolBarUICommands()`). The main
window's table only adds numpad Enter to the menu's Enter shortcuts
that have a modifier (`UICommand.accelerators()`).

In a text field (`wx.TextCtrl`, `wx.SearchCtrl` or the editors'
Scintilla fields, `_TEXT_FIELDS` in `uicommand.py`) Undo, Redo, Cut,
Copy, Paste, Delete and Select All act on its text, from the keyboard,
the menu or an editor's Ctrl+Z and Ctrl+Y. Undo takes back the typing
only, never text the program set:

| Field | Undo from | Note |
|-------|-----------|-------|
| Scintilla (editor fields) | Scintilla, every platform | history emptied when the program sets the text |
| `wx.TextCtrl`, `wx.SearchCtrl` on Windows | the native control | `EM_UNDO`, one level |
| the same on GTK; single-line ones on macOS | Task Coach (`workarounds/textundo.py`) | wxWidgets 3.2.8 leaves `Undo()` unimplemented there; GTK 3's entries have none |

`textundo` records each field's text before every key
(`EVT_CHAR_HOOK` on the app, which comes before accelerator tables
and the field), takes Ctrl+Z, Ctrl+Y and Ctrl+Shift+Z, and starts a
field's history over when the program sets its text (`SetValue`,
`ChangeValue`, `Clear`). Typing on, and deleting on, join one step;
password and read-only fields are left alone.

Undo and Redo are enabled whenever a text field has focus (it takes the
key for its own history) or the task history has a step.

---

## Key Files

| File | Role |
|------|------|
| `taskcoachlib/gui/uicommand/base_uicommand.py` | `MenuItem` subclass, `UICommand` base with `add_to_menu()` |
| `taskcoachlib/gui/uicommand/uicommand.py` | Concrete commands with `enabled()` overrides |
| `taskcoachlib/gui/uicommand/mixin_uicommand.py` | `PopupButtonMixin` (toolbar popup menu behavior) |
| `taskcoachlib/gui/menu.py` | `Menu.DestroyItem()` unbinds an item's handlers |
| `taskcoachlib/gui/viewer/base.py` | `has_selection` property, `is_tree_viewer()`, selection signals |
| `taskcoachlib/gui/toolbar.py` | `_Toolbar.DoIdleUpdate()` skips AGW's idle loop |
| `taskcoachlib/application/application.py` | `SetUpdateInterval(-1)`: no update events in idle time |
