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

Option C (the designer's idea, 2026-09-28) restores items with their
saved state (`__getstate__`, `__setstate__`). Mapped against the
model, that cannot restore exactly:

- Setting a state runs the edit rules again: a completed recurring
  task restored this way recurs twice (its due date moved 2 days).
- The state misses stored data: a task's reminder before snooze.
- Saved states share live lists (children, efforts) with the item, so
  later changes leak into them.
- A link held on one item and dated on another (a parent's children,
  an owner's notes and attachments, a task's efforts) is not restored
  with the item that points.
- The setters reset the modification date to now.
- Today a view reacting to an undo can run a command during it, which
  empties the redo list.

### Design, proposed 2026-09-30

C's idea kept, at the grain of the fields, as the ruling above words
it: every change dates its item, the log keeps what changed, in order,
one entry per user action.

1. **Storage units record.** Every stored value lives in a storage
   unit: `Attribute`, `SetAttribute`, and units for the links and
   lists (an item's parent and children, an owner's notes and
   attachments, a task's efforts, an effort's task, a container's
   items); the modification date is one too, and a task's reminder
   before snooze becomes an `Attribute`. At its first change within
   the open action, a unit gives the log its value before; when the
   action closes, the log takes each unit's value after.
2. **One action per user gesture.** A command opens the action; the
   commands run before the application is idle again join it (an
   editor's derived adjustments, posted events), as a platform undo
   manager groups by event loop pass. The first command names it
   ("Undo Edit subject"). Changes outside commands (scheduler, snooze,
   import, merge) record nothing.
3. **Undo and redo write values back, raw.** Undo writes each unit's
   value before, last change first; redo each value after, in order.
   The units send their change events and keep the derived indexes (a
   category's members, a task's dependencies), but no edit rule runs
   (completion and recurrence cascades, percentage, parent completion):
   their effects are units of the same action. One mode,
   `restoring()`, which a merge uses too (instead of `Task.merging()`).
4. **Nothing is done while restoring:** a command started by a view
   reacting to restored data does nothing.
5. **Commands only do.** `undo_command()`, `redo_command()`,
   `SaveStateMixin` and the date recorder go.
6. **A failed action rolls back** what it had changed.
7. **Outside the model.** The clipboard is not undone: a cut pastes its
   originals while they are out of the file, copies otherwise (one
   rule instead of the move flag). A tracking effort's stop comes back
   exactly: redo does not take a new "now".
8. **One side of each link:** a task's dependencies follow its
   prerequisites, as a category's members follow the items'
   categories; commands set the prerequisites only.

### Path

1. Every stored change sets the modification date: done
   ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)).
2. Storage units for the links, lists and containers; dependencies
   derived; `restoring()` gates the edit rules.
3. The log records and restores; commands lose their undo code, the
   existing do/undo/redo tests unchanged as the check.
4. Grouping by user gesture, rollback, the clipboard rule.

Group by action, not by time: two quick edits may share a second.

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
