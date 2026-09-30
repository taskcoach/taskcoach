# Persistence: XML Writer / Reader

How domain objects are serialized to `.tsk` XML files and deserialized back.

## Index

- [TODO](#todo)
- [Overview](#overview)
- [Defaults](#defaults)
- [Saving](#saving)
- [Merging](#merging)
- [Category Membership](#category-membership)
- [IDs](#ids)
- [Duplicate IDs](#duplicate-ids)
- [Related Documentation](#related-documentation)

---

## TODO

1. ~~Maybe always write values?~~ **Ruled by designer 2026-09-29:**
   no ([Defaults](#defaults)).
2. ~~The writer and reader decide defaults separately~~: done
   2026-09-29, one list ([Defaults](#defaults)).
3. ~~`plannedDurationMode` documented as "automatic"~~: resolved, the
   default is `"implicit"`.

---

## Overview

**File:** `taskcoachlib/persistence/xml/writer.py` (XMLWriter)
**File:** `taskcoachlib/persistence/xml/reader.py` (XMLReader)
**File:** `taskcoachlib/persistence/xml/defaults.py` (the defaults)

The writer serializes domain objects to XML and the reader
deserializes them back. A field holding its default is not written,
and a missing attribute is read as the default: both take the
defaults from one list.

---

## Defaults

**Ruling, 2026-09-29:** a field holding its default is not written;
a missing attribute is the default. Writing every value was ruled
out: it bloats the file for nothing (+118% measured on a generated
1,000-task file).

One list, `DEFAULTS` in `persistence/xml/defaults.py`, holds each
field's default. The writer (`is_default()`) and the reader (`read()`)
both use it, so they cannot disagree, and `XMLDefaultsTest` checks
that a new item holds each default, so the domain agrees too.

**Canon, ruled 2026-09-29:** a field's entry lists values. The first
is the default: an item holding it is saved without the attribute,
and a missing attribute is read as it. The others are other written
forms of it, read as the default, for a transition; the next save
leaves them out. A different default, not another form of it, also
needs the file version: files saved before the change mean the old
default by a missing attribute. A value that cannot be read is read
as the default.

| Kind | Fields | Default |
|---|---|---|
| A date not set | `plannedstartdate`, `duedate`, `actualstartdate`, `completiondate`, `reminder`, a recurrence's `stop_datetime`, a mail attachment's `sentDateTime` | the latest date ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#dates-not-set-is-the-latest-date)); `""` and `"None"` read as it |
| None | `fgColor`, `bgColor`, `font`; `shouldMarkCompletedWhenAllChildrenCompleted` (the preference decides); an effort's `stop` (still running) | none |
| Zero | `ordering`, `percentageComplete`, `priority`, `hourlyFee`, `fixedFee`, `stylePriority`, a recurrence's `count` and `max` (no maximum) | 0; `budget` and `plannedDuration` 0:00:00 |
| Empty | `subject`, `description`, `icon`, a recurrence's `unit`, a mail attachment's `fromName` and `fromAddress` ([EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md#fields)); `expandedContexts`, `prerequisites`, `categories`, `weekdays` | empty |
| False | `filtered`, `exclusiveSubcategories`, `sameWeekday`, `recurBasedOnCompletion` | False |
| Named | `plannedDurationMode`, an effort's `entryMode`, a recurrence's `amount` | `implicit`, `standard` (`""` reads as either), 1 |
| Another field | `reminderBeforeSnooze` (written while snoozed), `modificationDateTime` (written when known) | the reminder, the creation date |
| Unknown | `creationDateTime` | a date from before they were kept (`DateTime.min`) |

Always written, with no default: `id`, an attachment's `type` and
`location`, an effort's `start`. A task without a `recurrence` node
does not recur. `selectedIcon` (the open folder icon, removed
2026-09-28) is not read: an old file's value is dropped.

---

## Saving

Any change to saved data marks the file unsaved, and so starts an
autosave: an item's own data (every change to it sets its
modification date,
[ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)), an
item added or removed (to the file, or as a subitem, note, attachment
or effort), and saved view state (expanded, a category's filter).
Undo or redo back to the saved state clears the mark
([UNDO_REDO.md](UNDO_REDO.md#persistence)). Computed values, such as
a task's status, set no date and mark nothing ([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#to-do)
items 11 and 14).

`TaskFile.save()` (`persistence/taskfile.py`) writes what is in
memory; nothing on disk is merged ([Merging](#merging)).

1. It writes the XML through `SafeWriteFile`: to a temporary file next to
   the file, which replaces the file in one step (`os.replace`) only
   after the whole write, including the final flush, succeeded. The
   temporary file gets the file's mode first (not on Windows, where
   permissions are ACLs), and a task file that is a symbolic link is
   written through, so the link stays a link. In a synced cloud folder
   (Dropbox, ownCloud) the file is written in place instead, from a
   buffer, once the XML is complete; a failure during that write can
   still truncate it.
2. If writing fails, the file is left as it was (outside cloud
   folders).
3. Save As moves an existing file at the new name aside instead of
   deleting it, and puts it back if the save fails. Save and merge
   errors are shown to the user. A failed autosave is
   logged and tried again every minute (the file stays marked unsaved
   in the title); when the retry fails too, a notification tells the
   user once.

Locking is described in [FILE_LOCKING.md](FILE_LOCKING.md).

**Changed on disk (ruling, 2026-09-28).** Another program's change to
the open file (a sync client, an editor) is never replaced unasked.
The file watcher (`filesystem/`) reports a change, also a file
renamed over it (how editors, sync clients and Task Coach itself
write); `TaskFile.check_disk()` compares the file's size and
modification time with those at the last load or save, so our own
saves do not count. Every save checks too, before writing: the
watcher can report late, or not at all (some network drives).

- Saving raises `ChangedOnDiskError` and autosave pauses until the
  changes are merged in, the file is reloaded, or saved under another
  name.
- No unsaved changes: the user is asked once: Reload, Merge
  ([Merging](#merging)) or Later. Reload reads the file first (one
  that cannot be read changes nothing), then opens it as File > Open
  does.
- Unsaved changes: Merge (recommended), Save As or Later; Save asks
  the same, with Merge and save, Save As or Cancel.
- There is no Overwrite. Save As to the file's own name replaces it,
  after the file dialog's confirmation.
- A forced close (the session ends; nobody can be asked) saves the
  changes to a copy beside the file (`copy_name()`, "Tasks copy.tsk")
  and keeps the file as the other program left it.

## Merging

**Ruling, 2026-09-27:** one Task Coach per task file (the lock), so
nothing is merged when saving. The automatic merge with other
instances is removed: `merge_disk_changes()` on every save, the change
monitor and synchronizer, the `.delta` files, File > Merge disk
changes and the `autoload` setting (which nothing read). A `.delta`
file left by an older version is ignored.

File > Merge stays, to merge another file on request: a union, item by
item (`persistence/merge.py`). **Ruling, 2026-09-28:** the file to
merge is read into its own task file, separate from the open one and
only for the merge; the same ID in both is the same item.

- An item in only one file is kept.
- An item in both files (same ID) keeps its newer copy by
  modification date
  ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)).
  When a copy has no date (neither a creation nor a modification
  date: files from before the dates were kept), the file with the
  newest date of all its items wins; on a tie the
  open file keeps its copy. The merge gets more exact as more fields
  set the date.
- **Ruling, 2026-09-28:** a task's subtasks are the union of both
  files'. Each item names its parent and goes under the parent its
  winning copy names; a list of subitems is not data of its own and is
  never replaced by one file's.
- Notes, attachments and efforts are merged item by item too: each
  goes to the owner (and parent note) its winning copy names, so an
  edit to a task's note carries over even when the task's copy loses.
- Category membership comes from each task's or note's winning copy
  (they own their categories; a category's members are the reverse),
  a task's prerequisites from its winning copy (dependencies are their
  reverse).
- A merge replaces items by their winning copies and edits nothing,
  so no edit rule runs, the parent rules
  ([SCHEDULERS.md](SCHEDULERS.md#ssot-principle-scheduler-vs-events))
  included (`Task.merging()`). **Ruling, 2026-09-28:** the rules may
  run, as when adding subtasks in the editor, but not through a
  separate path for this fringe function; what they would change (a
  completed parent holding an open subtask from the other file) is
  left to the user.
- Deletions do not carry over: an item deleted in one file comes back
  from the other.

## Category Membership

**Asked by designer, 2026-09-29:** stored the same way in memory, in
the file and in the code: on the item that points, like a task's
prerequisites. Since tskversion 38 (release 2.0.3.0) a task's or
note's `categories` attribute lists its categories' IDs, sorted; a
note of a task, a category, an attachment or a note included. Only
categories in the file are written, so a template has none, as
before. The category node lists no members.

Older files stored it on the category: its `categorizables` attribute
(`tasks` before tskversion 19; before 14, category nodes inside the
task nodes). The reader turns those into the items' categories, and
the next save writes the new form. A release before 2.0.3.0 refuses a
version 38 file as too new (a check since 0.72.9) rather than losing
its categories.

## IDs

**Ruling, 2026-09-28:** a new item's ID is a random UUID, version 4
(`base.new_id()`): 122 random bits from the operating system's
cryptographic source (`os.urandom()`), no machine data, no time, in the
standard 36-character form, so two items never get the same ID. An ID
read from a file is kept as it is: older files have time-based UUIDs
(version 1), which never equal a version 4 one. Nothing depends on an
ID's form or order: sorting breaks ties by creation date first
([TASK_STATUS_SORT.md](TASK_STATUS_SORT.md#ties)). Copies get new IDs
([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#id-review)).

**Ruling, 2026-09-28:** the first paste after a cut is a move: it
pastes the cut items themselves, IDs kept (`Clipboard.items_to_paste()`);
further pastes, and pastes after a copy, insert copies with new IDs.
Since the undo log (2026-09-30) a cut pastes its items themselves
while the file does not hold them, so undoing that paste makes the
next paste a move again
([UNDO_REDO.md](UNDO_REDO.md#design-intent)).

**Ruling, 2026-09-28:** creation and modification dates are the
clock's time with microseconds (`date.Timestamp`). Only the same item's
dates are compared, in a merge; different items may share one (the ID
breaks sort ties).

The task file has no GUID since 2026-09-28: nothing read it after the
sync was removed. A file that has one still loads.

## Duplicate IDs

**Ruling, 2026-09-28:** an ID is unique within a file, fixed when the
file is read. The first item with an ID keeps it; each later one gets a
new ID (`XMLReader.__register_id()`), so references to the ID
(prerequisites, an older file's category members) mean the first; an
item's own categories stay its own. The file is marked
unsaved, and a message lists the items and how to keep or drop the
correction: Save, Save As, or close without saving; with autosave on,
the correction is saved at once and the file as it was can be restored
with File > Manage backups. The log lists them all.

---

## Related Documentation

- [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md) — Domain Attribute model,
  value normalization, setter/callback pattern
- [DATETIME_PRESETS.md](DATETIME_PRESETS.md) — Preset/propose modes and
  how they interact with persistence
- [DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md) — Duration modes,
  starting state documentation ("Start: Automatic mode")
