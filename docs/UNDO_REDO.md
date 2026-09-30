# Undo/Redo

## Table of Contents

1. [Design Intent](#design-intent)
2. [Architecture: Snapshot and Diff](#architecture-snapshot-and-diff)
3. [Actions](#actions)
4. [Persistence](#persistence)
5. [Modification Dates](#modification-dates)
6. [Commands](#commands)
7. [Testing](#testing)
8. [History](#history)
9. [References](#references)

## Design Intent

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

**The clipboard** (proposed 2026-09-30, built with the go-ahead): a cut
pastes its items themselves while the file does not hold them, copies
otherwise (`Clipboard.items_to_paste()`), so undoing a paste leaves the
cut items to paste again.

## Architecture: Snapshot and Diff

The designer's approach (2026-09-28, 2026-09-30): the file's content
in memory, compared before and after each action.

- **Fields:** every stored value of an item is a field
  (`patterns/field.py`): `Attribute` and `SetAttribute` for values and
  sets ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md)), `ListField` for
  an ordered list of items (a parent's subitems, an owner's notes and
  attachments, a task's efforts), `LinkField` for a link (a subitem's
  parent, an effort's task). Each copies its value (`snapshot()`) and
  puts one back (`restore()`), telling the views without dating the
  item. A computed (volatile) Attribute is not stored.
- **Registries:** every item registers when created; the open task
  file registers its lists (tasks, categories, notes); a view's list
  is not the file's and does not. All are held weakly
  (`patterns/snapshot.py`).
- **Snapshot:** every live item's fields, and which items each list
  holds. About 27 ms for a 2,000-task file, a comparison 2 ms
  (measured 2026-09-30).
- **Step:** the difference between the snapshots before and after an
  action: each field changed, with its values before and after, and
  the items added to or removed from each list. Items the action
  created are left out: undo takes them out of the lists.
- **Undo** writes the values before back into the same objects,
  inside `restoring()`: no edit rule runs (completion, recurrence,
  percentage, the actual start, a parent's completion, the exclusive
  subcategories' filter; their effects are in the step), no command
  does anything, no item is dated, and the views are told in one
  batch. **Redo** writes the values after.

## Actions

`CommandHistory().action(label)` (`patterns/command.py`) makes a user
action one step named label; `Command.do()` opens one. What is not a
command opens one itself: snoozing (`ReminderController`), stopping
tracking from the tray, File > Merge, the CSV and Todo.txt imports.

- **Nested actions join** the outer one.
- **One gesture is one step:** the step stays open until the
  application is next idle, when the events the action posted, and
  theirs, have run: what they change joins it, as undo managers group
  changes by event (Cocoa's `groupsByEvent`). An
  editor's follow-up adjustment (an effort's stop following its start,
  [DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md)) undoes with
  the edit that caused it. Without an event loop (tests, startup) the
  step closes at once; every read of the log closes it first.
- **A failed action is rolled back**, and its error raised again.
- **Views show undo and redo, they do not edit:** what a view does in
  reaction records nothing. An editor's field compares an edit with
  what it shows (a time without seconds), and the editors' dates logic
  runs only for the user's own edit
  ([DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md#preconditions-and-global-logic),
  0.5).
- **An action that changes nothing is no step** (a copy).

## Persistence

- The log is not saved. Undo and redo change stored data, so they
  mark the file unsaved like any change, and closing the file clears
  the log (`IOController`).
- Undo or redo back to the saved state clears the unsaved mark (ruling,
  2026-09-28): the file remembers the last step when it was saved or
  loaded (`TaskFile.mark_clean()`). A change made outside an action
  (the scheduler, an automatic import) makes that state unreachable
  until the next save (`TaskFile.mark_dirty()`).
- A change outside an action is not undoable. An undo writes back only
  what its step changed, over such a change to the same field.
- Merging files keeps the newest copy of each item by modification
  date ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)): undo leaves
  the dates exactly as before the change.

## Modification Dates

The modification date is a field like the others, so a step holds the
dates the action set, those of the items it changed in turn included
(a parent completed by its last subtask): undo puts back the dates
before, redo the dates after
([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)).
Nothing is dated while values are put back (`Object.modified_now()`),
merging included.

## Commands

A command only does (`do_command()`); the step is its undo and redo.
The flow of an edit:

```
User edit → AttributeSync → Command.do() → action → domain setter
  → Attribute.set() → callback → Publisher event → UI update
```

Until 2026-09-30, about 78 command classes had their own undo and redo:
values kept by the command, whole-item copies (`SaveStateMixin`,
`__getstate__`, `__setstate__`), items added and removed. A change that
spread to another item was undone only if the command kept a copy of
it. All of it is removed.

## Testing

- `tests/unittests/domainTests/UndoTest.py`: for each kind of change,
  the file written after undo is the file written before, dates
  included; redo gives the file after; no field differs in memory.
- `tests/unittests/guiTests/UndoWithEditorsTest.py`: the same cases
  with an editor open on each item; what an editor shows of a change,
  its undo or its redo, it writes nothing back.
- `tests/unittests/patternsTests/CommandTest.py`: the log (steps,
  joining, rollback, grouping by event).
- The command tests check each command's undo and redo.

## History

- **2026-09-27, ruling:** the undo log is a sequence of changes, each
  with the value before; one user action is one entry.
- **2026-09-28, option C:** object versions keyed by the modification
  date. The research (2026-09-30) found whole objects cannot be put
  back through their edit setters: the rules ran again (redo of
  completing a parent moved its recurring subtask's due date 2 days),
  the date was set to now, the reminder before snooze was missed, live
  lists were shared, and links stored on the other side did not come
  back.
- **2026-09-30:** the designer's snapshot and diff, at the grain of
  the fields; built the same day.

## References

- [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md): stored fields, change
  notification, the modification date ruling
- [PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging): merging by
  modification date
- [DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md): the editors'
  duration sync
- `taskcoachlib/patterns/field.py`: `Field`, `ListField`, `LinkField`
- `taskcoachlib/patterns/snapshot.py`: `Snapshot`, `Step`,
  `restoring()`
- `taskcoachlib/patterns/command.py`: `Command`, `CommandHistory`
- `taskcoachlib/command/`: the commands
- `taskcoachlib/gui/dialog/attributesync.py`: AttributeSync
