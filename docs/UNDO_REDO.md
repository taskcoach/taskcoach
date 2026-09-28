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

### Options

**A. Undo code per command (today).** Each command class undoes its
own changes (below, Current Implementation). Changes that spread to
other items are undone only when the command thought of them; about
78 classes to keep right.

**B. Field log.** The storage units (Attribute, SetAttribute, the
links) record each change into the open entry: item, field, value
before, modification date before. Undo sets them back in reverse,
redo sets the values after. Complete once every stored field is a
storage unit; many small records per action.

**C. Object versions, keyed by modification date (recommended).**
Every stored change sets its item's modification date: that is the
moment the log saves the item's version before the change (its saved
state, as the file has it, date included), under its UUID, once per
action. Changes that spread set their items' dates too, so they are
logged, in order, without the command knowing about them. An entry is
an action number and the UUIDs it changed, each with its version
before and, at the end of the action, after. Undo puts the versions
before back into the same objects, in reverse; redo the versions
after. Items created or deleted have no version before or after, and
are removed or re-added. Open editors, selection and the tree stay,
since the objects stay.

**D. Whole-file or whole-model versions.** Save a copy of everything
per action, undo reloads the previous one. Simple, but every undo
rebuilds all objects (open editors, selection and the tree are lost,
the scheduler rebuilds) and costs as much as opening the file; a full
copy per edit. Earlier versions of the file already exist as backups
(File > Manage backups).

### Path for C

1. Every stored change sets the modification date: the migration
   table ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)),
   links included. This is its purpose as well as merging.
2. Save an item's version at its first change within an action, from
   the same place that sets the date, before the change is written.
   Commands keep their own undo code meanwhile: restoring an item to
   the same state twice is harmless, and each command's existing
   do/undo/redo test checks every step.
3. Drop the undo code of commands whose fields are all covered, then
   of the others as their fields are migrated; record adding and
   removing items, then drop the undo code of new, delete, cut and
   paste, and `SaveStateMixin`.
4. Derived adjustments land in the entry of the action that caused
   them, not in entries of their own (below, Command Pattern).
5. The date recorder (below, Modification Dates) goes: the versions
   include the dates.

Group by action number, not by time: two quick edits may share a
second. The modification date keeps fractions of a second anyway
([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)).

### Persistence

- The log is not saved. Undo and redo change stored data, so they
  mark the file unsaved like any change, and closing the file clears
  the log (`IOController`).
- Undo or redo back to the saved state clears the unsaved mark (ruling,
  2026-09-28): the file remembers the last command done when it was
  saved or loaded. A change made outside a command (expanding a task,
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
manages value storage, change detection, and pubsub notification. Commands
call the domain setter (e.g., `effort.setDuration()`), which delegates to
`Attribute.set()`. The Attribute fires its callback only on actual change,
which sends pubsub notifications. AttributeSync in the editor subscribes to
these notifications and updates the UI.

The flow:

```
User edit → AttributeSync → Command.do() → domain setter → Attribute.set()
  → callback (on change) → pubsub → AttributeSync.onAttributeChanged → UI update
```

## References

- [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md) — Attribute storage, change
  detection, and pubsub notification pattern; modification date ruling
- [PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging): merging by
  modification date
- [DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md) — Duration sync calc
  logic for tasks and efforts
- `taskcoachlib/patterns/command.py`: `Command`, `CommandHistory`
- `taskcoachlib/command/base.py` — Base command classes
- `taskcoachlib/command/effortCommands.py` — Effort-specific commands
- `taskcoachlib/command/taskCommands.py` — Task-specific commands
- `taskcoachlib/gui/dialog/attributesync.py` — AttributeSync (Layer 2 wiring)
