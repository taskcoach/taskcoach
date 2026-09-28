# Persistence: XML Writer / Reader

How domain objects are serialized to `.tsk` XML files and deserialized back.

## Index

- [TODO](#todo)
- [Overview](#overview)
- [Writer Skip Conditions](#writer-skip-conditions)
  - [Task Node](#task-node)
  - [Recurrence Node](#recurrence-node)
  - [Effort Node](#effort-node)
  - [Category Node](#category-node)
  - [Base Node (All Objects)](#base-node-all-objects)
- [Reader Defaults](#reader-defaults)
- [Round-Trip Consistency](#round-trip-consistency)
- [Skip Condition Categories](#skip-condition-categories)
- [Saving](#saving)
- [Merging](#merging)
- [Related Documentation](#related-documentation)

---

## TODO

1. **Maybe always write values?** The writer omits attributes when the value
   equals an assumed default. This scatters default-value knowledge across
   the writer instead of centralizing it in the domain (Attribute pattern).
   Always writing every attribute would make the XML slightly larger but
   eliminate the implicit "is this worth saving" decision and the risk of
   writer/reader default mismatch. At minimum, the writer and reader should
   share a common source of truth for defaults.

2. The writer and reader independently decide defaults in two different
   files with no shared constant or domain method connecting them. They
   agree by convention, not by contract. If one changes without the other,
   round-trip silently corrupts data.

3. ~~`plannedDurationMode` skip condition uses hardcoded `"implicit"` but
   the documented default starting state is "automatic"~~ — **Resolved.**
   The actual code default is `"implicit"` (task.py:52). The
   DURATION_CALCULATIONS.md documentation has been corrected to match.
   Writer and reader both agree on `"implicit"` as the default.

---

## Overview

**File:** `taskcoachlib/persistence/xml/writer.py` (XMLWriter)
**File:** `taskcoachlib/persistence/xml/reader.py` (XMLReader)

The writer serializes domain objects to XML. For each field, it checks
whether the value equals an assumed default — if so, the XML attribute is
**omitted entirely** (not written as an empty string). The XML element has
no trace of the attribute.

The reader deserializes XML back to domain objects. For each field, if the
XML attribute is missing, the reader provides its own default via
`.get("attributeName", default)`.

These two default decisions are made independently. They happen to agree
by convention.

---

## Writer Skip Conditions

The writer conditionally omits attributes from the XML. "Skipped" means
the attribute is **not written to XML at all** — completely absent from
the element, not written as an empty value.

### Task Node

`taskNode()` — lines 144-199:

| Line | XML Attribute | Skip Condition | Type |
|------|--------------|----------------|------|
| 148 | `plannedstartdate` | `== maxDateTime` | Sentinel |
| 150 | `duedate` | `== maxDateTime` | Sentinel |
| 152 | `actualstartdate` | `== maxDateTime` | Sentinel |
| 154 | `completiondate` | `== maxDateTime` | Sentinel |
| 156 | `percentageComplete` | `== 0` (falsy) | Falsy |
| 158 | `recurrence` | empty Recurrence (falsy) | Falsy |
| 160 | `budget` | `== TimeDelta()` | Sentinel |
| 162 | `plannedDuration` | `== TimeDelta()` | Sentinel |
| 164 | `plannedDurationMode` | `!= "implicit"` (inverted) | Hardcoded string |
| 166 | `priority` | `== 0` (falsy) | Falsy |
| 168 | `hourlyFee` | `== 0` (falsy) | Falsy |
| 170 | `fixedFee` | `== 0` (falsy) | Falsy |
| 173 | `reminder` | `== maxDateTime` | Sentinel |
| 187 | `prerequisites` | empty string (falsy) | Falsy |
| 189 | `shouldMarkCompleted...` | `== None` | None check |

`maxDateTime` is the date not set, the latest date
([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#dates-not-set-is-the-latest-date));
the reader gives it back for a missing attribute.

### Recurrence Node

`recurrenceNode()` — lines 201-217:

| Line | XML Attribute | Skip Condition | Type |
|------|--------------|----------------|------|
| 203 | `amount` | `<= 1` | Numeric compare |
| 205 | `count` | `<= 0` | Numeric compare |
| 207 | `max` | `<= 0` | Numeric compare |
| 209 | `stop_datetime` | `== maxDateTime` | Sentinel |
| 211 | `sameWeekday` | falsy (`False`) | Falsy |
| 213 | `recurBasedOnCompletion` | falsy (`False`) | Falsy |
| 215 | `weekdays` | falsy (empty) | Falsy |

### Effort Node

`effortNode()` — lines 219-239:

| Line | XML Attribute | Skip Condition | Type |
|------|--------------|----------------|------|
| 234 | `entryMode` | falsy or `== "standard"` | Hardcoded string |
| | `creationDateTime`, `modificationDateTime` | `<= DateTime.min` | Sentinel; with microseconds (`date.Timestamp`) |

### Category Node

`categoryNode()`:

| XML Attribute | Skip Condition | Type |
|--------------|----------------|------|
| `filtered` | falsy (`False`) | Falsy |
| `exclusiveSubcategories` | falsy (`False`) | Falsy |
| `stylePriority` | `== 0` (falsy) | Falsy |

### Base Node (All Objects)

`__baseNode()` / `baseNode()` / `baseCompositeNode()` — lines 286-353:

| Line | XML Attribute | Skip Condition | Type |
|------|--------------|----------------|------|
| 292 | `creationDateTime` | `<= DateTime.min` | Sentinel; written with microseconds (`date.Timestamp`) |
| 294 | `modificationDateTime` | `<= DateTime.min` | Sentinel; written with microseconds (`date.Timestamp`) |
| 298 | `subject` | `""` (falsy) | Falsy |
| 300 | `description` | `""` (falsy) | Falsy |
| 308 | `fgColor` | `None` (falsy) | Falsy |
| 310 | `bgColor` | `None` (falsy) | Falsy |
| 312 | `font` | `None` (falsy) | Falsy |
| 314 | `icon` | `""` (falsy) | Falsy |
| 316 | `selectedIcon` | `""` (falsy) | Falsy |
| 318 | `ordering` | `== 0` (falsy) | Falsy |
| 345 | `expandedContexts` | empty (falsy) | Falsy |

---

## Reader Defaults

When an XML attribute is missing, the reader provides a default via
`.get("attr", default)`. Selected examples from `_parse_task_node()`:

| XML Attribute | Reader Default | Matches Writer Skip? |
|--------------|---------------|---------------------|
| `subject` | `""` | Yes — writer skips `""` |
| `plannedstartdate` | not set → `None` → `maxDateTime` | Yes |
| `percentageComplete` | `"0"` → `0` | Yes |
| `priority` | `"0"` → `0` | Yes |
| `plannedDurationMode` | `"implicit"` | Yes — code default is `"implicit"` (task.py:52) |
| `budget` | `""` → `TimeDelta()` | Yes |
| `hourlyFee` | `"0"` → `0.0` | Yes |

---

## Round-Trip Consistency

A value round-trips correctly when:

```
domain.getValue() → writer skips → XML has no attribute → reader defaults → domain.setValue(default)
```

...produces the same value as the original. This works today for all fields
because the writer skip conditions and reader defaults happen to agree.

**Risk:** If the writer's skip condition or the reader's default is changed
independently, the round-trip breaks silently. There is no shared constant,
no assertion, and no test that verifies writer/reader default agreement.

---

## Skip Condition Categories

The writer uses several types of skip conditions, with varying levels of
correctness:

**Sentinel-based** (dates, budget, duration) — Comparing against an
explicit "no value" marker defined by the domain (`maxDateTime`,
`TimeDelta()`). Semantically correct — the sentinel means "not set."

**Falsy-based** (strings, numbers, booleans) — Using Python truthiness
(`if value:`). This conflates multiple concepts:
- `""` is falsy — but `""` is a valid string value (user cleared subject)
- `0` is falsy — but `0` is a valid numeric value (priority 0, zero fee)
- `None` is falsy — genuinely means "not set"
- `False` is falsy — valid boolean value

These work by accident because the falsy value happens to match the
constructor default. They'd break if any default changed to a non-falsy
value.

**Hardcoded string** (`plannedDurationMode`, `entryMode`) — Comparing
against a string literal that the writer assumes is the default. The
domain constructor defines the actual default separately. If they
diverge, data is silently lost.

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
a task's status, set no date and mark nothing ([MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#steps)
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

## Merging

**Ruling, 2026-09-27:** one Task Coach per task file (the lock), so
nothing is merged when saving. The automatic merge with other
instances is removed: `merge_disk_changes()` on every save, the change
monitor and synchronizer, the `.delta` files, File > Merge disk
changes and the `autoload` setting (which nothing read). A `.delta`
file left by an older version is ignored.

File > Merge stays, to merge another file on request: a union, item by
item (`persistence/merge.py`).

- An item in only one file is kept.
- An item in both files (same ID) keeps its newer copy by
  modification date
  ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)).
  When a copy has no date (neither a creation nor a modification
  date: files from before the dates were kept), the file with the
  newest date of all its items wins; on a tie the
  open file keeps its copy. The merge gets more exact as more fields
  set the date.
- Each item goes under the parent its winning copy names, so subitems
  from both files end up together.
- Notes, attachments and efforts are merged item by item too: each
  goes to the owner (and parent note) its winning copy names, so an
  edit to a task's note carries over even when the task's copy loses.
- Category membership comes from each task's or note's winning copy
  (they own their categories; a category's members are the reverse),
  a task's prerequisites from its winning copy (dependencies are their
  reverse).
- Merged items keep the dates and data of their winning copies:
  rebuilding links is not an edit. A subtask list is derived from the
  subtasks' parents, so the automatic parent rules (a parent completed
  when all its subtasks are, reopened by an open subtask) do not run
  while a merge rebuilds it (`Task.rebuilding_links()`).
- Deletions do not carry over: an item deleted in one file comes back
  from the other.

---

## Related Documentation

- [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md) — Domain Attribute model,
  value normalization, setter/callback pattern
- [DATETIME_PRESETS.md](DATETIME_PRESETS.md) — Preset/propose modes and
  how they interact with persistence
- [DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md) — Duration modes,
  starting state documentation ("Start: Automatic mode")
