# Undo/Redo

## Table of Contents

1. [TODO: One Undo Log](#todo-one-undo-log)
2. [Current Implementation](#current-implementation)
3. [Modification Dates](#modification-dates)
4. [Command Pattern](#command-pattern)
5. [Interaction with Attribute Pattern](#interaction-with-attribute-pattern)
6. [References](#references)

## TODO: One Undo Log

**Ruling, 2026-09-27:** the undo log is a simple sequence of changes,
each with the value before it changed. For a field of an item with a
modification date, the entry holds the field's value before and the
item's modification date before. Every kind of change works the same
way. One user action is one entry.

### Design Intent

**Ruled by designer 2026-09-30** (points 1 to 3; 4 proposed, view
state ruled 2026-09-28): one universal undo, no code per command nor
per case, standard behaviour.

1. **Every user action that changes the file is one step:** commands,
   editor edits, snoozing a reminder, tracking started or stopped from
   the tray, File > Merge, imports. The step is named after the
   action ("Undo Snooze").
2. **A step holds everything the action changed**, what the edit rules
   changed in turn included (a parent completing its subtasks, a
   recurrence moving the dates).
3. **Standard behaviour:** undo and redo walk the steps; a new action
   clears the redo steps; opening or closing a file clears them all;
   undo or redo back to the saved state clears the unsaved mark.
4. **Not steps:** changes the program makes on its own (the scheduler,
   automatic imports), view state (expanded rows, a category's filter)
   and the clipboard.

### Architecture: Snapshot and Diff

The designer's approach (2026-09-28, 2026-09-30): the file's content
in memory, compared before and after each action.

- **Snapshot:** every saved value of every item in the file, read by
  one generic loop over the items' fields, and which items the file
  holds. About 27 ms for a 2,000-task file, a comparison 2 ms
  (measured 2026-09-30).
- **Step:** a snapshot when the action starts and one when it ends;
  the difference is the step: the items changed, with their values
  before and after, and the items added to or removed from the file.
- **Undo** writes the values before back into the same objects, as
  loading a file does: no edit rule runs (their effects are in the
  step), the views are told. **Redo** writes the values after.
- **Nothing is recorded while undoing or redoing:** a view reacting to
  it starts no action.

What the model needs: every saved value is a field of the attribute
pattern ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md)), so the snapshot
reads and writes them all the same way. Missing on 2026-09-30:

- a task's reminder before snooze, a plain value;
- the links and lists: a subitem's parent and the parent's subitems,
  an owner's notes and attachments, a task's efforts and an effort's
  task, a task's dependencies;
- one switch that turns the edit rules off while values are put back
  (completion, recurrence, percentage, parent completion), used by
  merging too (instead of `Task.merging()`).

Findings on today's copy code (`__getstate__`, `__setstate__`),
checked 2026-09-30, which the snapshot replaces: it restores through
the edit setters, so the rules run again (redo of completing a parent
moved its recurring subtask's due date 2 days); it sets the
modification date to now; it misses the reminder before snooze; it
shares live lists with the item.

### Path

1. The model: the fields above, and the edit rules' switch.
2. The snapshot log beside today's undo, in check mode: after each
   undo, an item that differs from the snapshot is logged.
3. Undo and redo from the log; the commands lose their undo code; the
   actions outside commands (snooze, tray, merge, imports) become
   steps.

### Persistence

- The log is not saved. Undo and redo change stored data, so they
  mark the file unsaved like any change, and closing the file clears
  the log (`IOController`).
- Undo or redo back to the saved state clears the unsaved mark (ruling,
  2026-09-28): the file remembers the last command done when it was
  saved or loaded, and moves that along over commands that change
  nothing (a copy); a command enters the log once done, as undo and
  redo notify after running. A change made outside a command (expanding a task,
  a merge, snoozing) makes that state unreachable until the next save
  (`TaskFile.on_command_history_changed()`).
- Changes outside a user action (the scheduler, a Todo.txt import,
  snoozing in the reminder window) are not undoable and record into
  no entry. An undo that restores an item overwrites such a change
  made to it after the action.
- Merging files keeps the newest copy of each item by modification
  date ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)), so undo
  must leave the dates exactly as before the change.

## Current Implementation

`CommandHistory` (`patterns/command.py`) keeps two lists, done and
undone commands, and is cleared when the file closes. About 78 command
classes (`command/`) each implement `do_command()`,
`undo_command()` and `redo_command()`, in three ways:

- **Field values kept by the command** (edit subject, description,
  dates, priority, fees, style priority): undo sets the old values
  back.
- **Saved item copies** (`SaveStateMixin`, `__getstate__` and
  `__setstate__`: mark completed, active or inactive, percentage
  complete, new subtask, paste, drag and drop): undo restores the
  whole copy, modification date included.
- **Adding and removing items** (new, delete, cut): undo removes or
  re-adds them.

A change that spreads to another item is undone only if the command
saved a copy of that item.

## Modification Dates

Undo puts back every modification date the change set, including
those of items it changed in turn; redo puts back the dates from the
change ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)).

Until the log above exists, this is the date part of it:
`ModificationDateRecorder` (`domain/base/object.py`) records each
item's date before its first change while a command runs;
`BaseCommand.do()` keeps the dates before and after the change, and
`undo()` and `redo()` set them back (`command/base.py`). Field values
are still undone per command, as listed above.

## Command Pattern

Commands wrap **all** field changes, including derived value adjustments.
For example, when the user changes a start date:

1. `EditEffortStartDateTimeCommand` fires, writing the new start to the domain.
2. The sync calc (`__sync_effort_state`) detects that duration must be
   recalculated and fires `EditEffortDurationCommand` to adjust duration.

Both commands land on the undo stack. Undoing the start change does **not**
automatically undo the derived duration adjustment — each command is
independent on the stack. Path step 4 above fixes this.

## Interaction with Attribute Pattern

The Attribute pattern (see [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md))
manages value storage, change detection, and change notification. Commands
call the domain setter (e.g., `effort.setDuration()`), which delegates to
`Attribute.set()`. The Attribute fires its callback only on actual change,
which sends Publisher events. AttributeSync in the editor subscribes to
these notifications and updates the UI.

The flow:

```
User edit → AttributeSync → Command.do() → domain setter → Attribute.set()
  → callback (on change) → Publisher event → AttributeSync.on_attribute_changed → UI update
```

## References

- [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md) — Attribute storage, change
  detection, and change notification pattern; modification date ruling
- [PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging): merging by
  modification date
- [DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md) — Duration sync calc
  logic for tasks and efforts
- `taskcoachlib/patterns/command.py`: `Command`, `CommandHistory`
- `taskcoachlib/command/base.py` — Base command classes
- `taskcoachlib/command/effortCommands.py` — Effort-specific commands
- `taskcoachlib/command/taskCommands.py` — Task-specific commands
- `taskcoachlib/gui/dialog/attributesync.py` — AttributeSync (Layer 2 wiring)
