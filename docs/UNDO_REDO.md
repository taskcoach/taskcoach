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

**C. Object versions, keyed by modification date (the designer's
idea, 2026-09-28; see Findings).** Every stored change sets its
item's modification date: that is the
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

### Findings, 2026-09-30

Option C (the designer's idea, 2026-09-28) is sound: a full copy of
what the file stores for each changed item, put back on undo, as if
reopening the previous version for those items only. Today's copy and
restore code (`__getstate__`, `__setstate__`) is not such a copy;
checked in memory:

- **It restores through the editing setters, so the edit rules run
  again.** Redo of completing a parent (which completed its recurring
  subtask and cleared the subtask's recurrence) moved the subtask's
  due date 2 days: the completion date is set back before the
  recurrence, so the subtask recurs. Loading a file runs no such rule.
- **It sets the modification date to now** instead of the copy's date.
- **It misses a stored field:** the reminder before snooze (a snoozed
  task's original reminder, from which a recurring task computes its
  next reminder). The reminder itself comes back.
- **It shares live lists** (subtasks, efforts) with the item, so later
  changes leak into the copy.
- **A copy is taken only of the item that points:** moving a subtask
  changes the old and new parent's lists of subtasks, an owner's notes
  and a task's efforts likewise, and these items' dates do not change.
- **No hook runs before a stored value changes:** the value is written
  first, the date after.
- By reading the commands, not reproduced: an editor can run a command
  during an undo, which empties the redo list.

### Design, proposed 2026-09-30

Option C, with copies that are exact:

1. **The copy is what the file stores** for the item: every stored
   field, its links and its own lists, copied (not shared), the
   modification date included.
2. **Taken before the first change** within an action, from the one
   place every stored change passes, and taken of every item whose
   stored data changes: the item that points and the items holding the
   other side (a parent's subtasks, an owner's notes and attachments, a
   task's efforts). Items added to or removed from the file are
   recorded as such.
3. **Put back as loading does:** stored values set directly, no edit
   rule run (completion, recurrence, percentage, parent completion),
   their effects being copies of the same action; the views are told.
   Redo puts back the copies taken when the action ended.
4. **Nothing is done while putting back:** a command a view starts in
   reaction does nothing.
5. **One user action is one entry**, derived adjustments included.

Whole-file versions (D) give the same result and remain the fallback.

### Path

Small steps, each safe on its own:

1. **Check mode:** the copies are taken beside today's undo, changing
   nothing; after each undo an item that differs from its copy is
   logged. This measures where today's undo is wrong.
2. **Undo finishes from the copies:** after a command's own undo, the
   copies are put back. The commands stay as they are.
3. **Per-command undo code goes,** one family of commands at a time,
   where check mode shows the copies cover it.

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
