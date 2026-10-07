# Persistence: XML Writer / Reader

How domain objects are serialized to `.tsk` XML files and deserialized back.

## Index

- [TODO](#todo)
- [Overview](#overview)
  - [Files From Others](#files-from-others)
- [Defaults](#defaults)
- [Saving](#saving)
  - [Watching the File](#watching-the-file)
- [Backups](#backups)
- [Merging](#merging)
- [Category Membership](#category-membership)
- [IDs](#ids)
- [Duplicate IDs](#duplicate-ids)
- [Versions and Compatibility](#versions-and-compatibility)
- [Related Documentation](#related-documentation)

---

## TODO

1. ~~Maybe always write values?~~ **Ruled by designer 2026-09-29:**
   no ([Defaults](#defaults)).
2. ~~The writer and reader decide defaults separately~~: done
   2026-09-29, one list ([Defaults](#defaults)).
3. ~~`plannedDurationMode` documented as "automatic"~~: resolved, the
   default is `"implicit"`.
4. Retire the forms written for older releases (`legacy.py`): in
   place since 2.0.3.0, 2026-10-01; review between January and April
   2027 ([To Do: Retire the Old
   Forms](#to-do-retire-the-old-forms)).

---

## Overview

**File:** `taskcoachlib/persistence/xml/writer.py` (XMLWriter)
**File:** `taskcoachlib/persistence/xml/reader.py` (XMLReader)
**File:** `taskcoachlib/persistence/xml/defaults.py` (the defaults)

The writer serializes domain objects to XML and the reader
deserializes them back. A field holding its default is not written,
and a missing attribute is read as the default: both take the
defaults from one list. A file saved before stored text dropped the
characters XML forbids may hold them: the reader drops them, raw or
as references, before parsing
([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#text)).

Both use the standard library's ElementTree (lxml until 2.0.3.0). Its
parsed tree keeps nothing before the root element, so the reader takes
the `<?taskcoach?>` line ([Two Numbers](#two-numbers)) from the
parser's events, and Help > Anonymize writes it back.

### Files From Others

A task file or template may come from anyone. A DOCTYPE is refused
before the file is parsed (`reader._refuse_doctype()`, since
2026-10-06): Task Coach never wrote one, and with it go every entity,
external DTD and parameter entity, the crash below included
(`XMLReaderDoctypeTest`). The standard library's parser, Expat, never
reads another file or the network: an external entity is refused as
undefined, an external DTD is not fetched. Since Expat 2.4 it refuses
entity expansion bombs (billion laughs, quadratic blowup). Expat is
the system's, or on Windows and macOS Python's own: those builds run
Python 3.13.16, with Expat 2.8.5, and each build stops on an Expat
older than 2.7.2 ([Expat by Package](#expat-by-package)). lxml before 5.0 read a local
file named in an external entity
into the task by default (its 5.0 changelog); Ubuntu 22.04 ships
4.8.0, Debian 12 4.9.2. What the writer saves is escaped: markup typed
into a field comes back as the same text.

Checked 2026-10-03 with hostile files, in the app and through the
reader: an external entity naming a local file or a URL, an external
DTD and parameter entity (a local web server logged no request),
XInclude, billion laughs and quadratic blowup (refused in 0.2 s), 60
MB of text in one field (read), 100,000 nested tasks (refused: the
reader's recursion limit; lxml stops at 256 levels). The refused files
show the usual file error dialog.

### Expat by Package

Measured 2026-10-06: the version inside each build's Python; the
distributions' from their archives and security trackers.

| Package | Python | Expat |
|---|---|---|
| Windows | python.org 3.11.9, embeddable | 2.6.0, Python's own |
| macOS | setup-python "3.11": python.org 3.11.9 (macOS 11) | 2.6.0, Python's own |
| AppImage | python-appimage's latest 3.11: 3.11.17 | 2.8.5, its own |
| Flatpak | the GNOME 50 runtime (freedesktop SDK 25.08) | 2.7.1, the runtime's |
| Debian 12, 13 | the system's | 2.5.0 and 2.8.3, with backported fixes |
| Ubuntu 22.04, 24.04 | the system's | 2.4.7 and 2.6.1, with backported fixes |
| Fedora 43, Arch | the system's | 2.8.5 |

Python 3.11 has had no Windows or macOS build since 3.11.9 (April
2024); its later releases, source only, bundle newer Expat (3.11.17:
2.8.5). Since To Do 27 (2026-10-06) the Windows, macOS and AppImage
builds carry Python 3.13 (Expat 2.8.5), and each stops on an Expat
older than 2.7.2. Ubuntu 22.04 leaves CVE-2025-59375 and CVE-2026-45186 unfixed
("changes too intrusive"); the Flatpak runtime lacks the fixes from
2.7.2 on.

Expat has had 15 releases since 2.6.0, with over 40 CVEs (its
`Changes`), 2.9.0 on 2026-10-05. Through Task Coach's reader
(ElementTree's pull parser fed UTF-8 text, internal entities
expanded, no external entity parser; 64-bit builds):

- Reached and seen, CVE-2024-8176 (fixed in 2.7.0): a chain of
  entities crashes the process. With Expat 2.6.0 built from its
  release and loaded in place of the system's, `reader.parse()`
  crashed on a task file of 20,000 chained entities (525 KB, 101 KB
  gzipped) with a 2 MB stack, as on Windows, and of 100,000 (2.7 MB)
  with 8 MB, as on macOS; 15,000 and 50,000 were read. Expat 2.8.3
  read them all within 0.2 s. The last file setting is written at
  quit, so the next start opens the file before.
- Of the same kind, not reproduced: memory blow-up (CVE-2025-59375,
  2.7.2; its published reproducer is refused through the reader, as
  with 2.8.3) and slow parsing from crafted attributes or weak hash
  salts (2.8.0, 2.8.1, 2.8.4): a file that holds Task Coach or its
  memory while it opens.
- Not reached by Task Coach's use: the ones that need an external
  entity parser, a negative length, a 32-bit build, UTF-16 input, a
  handler calling back into the parser, or `xmlwf`.

Ways out for Windows and macOS (To Do 82 in
[REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md#to-do) 4):

- Python 3.13.16 (Expat 2.8.5): the series the suite runs on
  (3.13.5 on its certified platform, [TESTING.md](TESTING.md)), and
  3.13's last release with Windows and macOS builds (2026-10-01,
  PEP 719); Expat stays at 2.8.5 from then on.
- Python 3.14 (3.14.8, Expat 2.8.5): builds until October 2027
  (PEP 745). Fedora 43 and Arch run Task Coach on it already (CI
  imports it only); the suite has not run on it.
- A DOCTYPE refused by the reader: Task Coach never wrote one (only
  the HTML export does). It stops every entity-based attack in every
  package, the crash above included, and none of the others.

Done 2026-10-06, both: the builds on Python 3.13 (To Do 27) and the
DOCTYPE refused. With Expat 2.6.0 and a 2 MB stack, the app given the
20,000-entity file as its last file crashed at every start before
("Fatal Python error: Segmentation fault"); now it shows the file
error and runs on. The check reads only what comes before the root:
0.035 ms on a 10,000-task file whose parse takes 42 ms.

On 3.13 and 3.14 alike, wxPython 4.3.1, pywin32 312 and py2app 0.28.10
have builds, and Windows 8.1 and macOS 11 stay the minimums.

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
| Another field | `reminderBeforeSnooze` (written while snoozed), `modificationDateTime` (written when it differs from the creation date, or the file stated it: [Versions and Compatibility](#versions-and-compatibility)) | the reminder, the creation date |
| Unknown | `creationDateTime` | a date from before they were kept (`DateTime.min`) |

Always written, with no default: `id`, an attachment's `type` and
`location`, an effort's `start`. A task without a `recurrence` node
does not recur. `selectedIcon` (the open folder icon, removed
2026-09-28) is not used: it is written back as read, for older
releases ([Versions and Compatibility](#versions-and-compatibility)).

---

## Saving

Two ways, **ruled by designer 2026-10-07**: autosave (Preferences >
Files, on by default) or File > Save on demand. "There should not be
a third mode": saving when Task Coach loses focus (TODO.md 3) was
dropped.

Autosave takes two steps:

1. **The change reaches the task.** Text typed in the subject,
   description, dates, durations and amounts counts when the user
   leaves the field: Tab, a click elsewhere, closing the editor,
   another program
   ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#todo) 1). Until then
   it is only in the field: a crash loses it. Checkboxes, choices, the
   priority, menu commands, drags and undo count at once.
2. **The file is saved** (`persistence/autosaver.py`) once the change
   and what it sets off (tied dates, a parent completed, the next
   recurrence) are done: at wx's next idle event, sent as soon as no
   event is waiting, milliseconds later. No timer, no waiting for the
   user to pause; the changes of one action make one save.

Checked 2026-10-07 on Linux (openbox): a subject typed in the task
editor was saved 4 ms after another window took the focus. The lists'
edit boxes do the same
([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#in-place-editing)). Windows
and macOS not checked.

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
   after the whole write succeeded and is on disk (`fsync`); then the
   folder's entry is put on disk too (`filesystem/ondisk.py`), so a
   power cut right after a save leaves the old file or the new. The
   temporary file gets the file's mode first (not on Windows, where
   permissions are ACLs), and a task file that is a symbolic link is
   written through, so the link stays a link. In a synced cloud folder
   (Dropbox, ownCloud) the file is written in place instead, from a
   buffer, once the XML is complete, and put on disk; a failure during
   that write can still truncate it.
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
The file watcher ([below](#watching-the-file)) reports a change within
seconds, also a file renamed over it (how editors, sync clients and
Task Coach itself write); `TaskFile.check_disk()` compares the file's
size and modification time with those at the last load or save, so
our own saves do not count. Every save checks too, before writing,
so a change the watcher has not reported yet is never written over.

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
- A forced close (the session ends: a Windows session end, SIGTERM
  or SIGHUP; nobody can be asked, [SESSION_END.md](SESSION_END.md))
  saves the changes to a copy beside the file (`copy_name()`, "Tasks
  copy.tsk") and keeps the file as the other program left it.

### Watching the File

**Ruled by designer 2026-10-03** (To Do 79 in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#to-do)):
Task Coach checks the open file's modification time and size every 10
seconds (`filesystem/watcher.py`), in a thread that runs while a file
is open. Any difference from what it last saw, an older time too (a
restored copy), goes to `TaskFile.check_disk()` on the user interface
thread, which asks as above. It is the same on every system and on
network shares, where a change made from another computer counts too.
It replaced the watchdog package and the Preferences option "Use
polling for file monitoring", dropped from settings files on load.

Measured in the app, 2026-10-03:

- A check takes 12 to 30 microseconds and reads nothing from the
  disk: the system keeps a file's details in memory, and a check does
  not change its access time, so a sleeping drive stays asleep.
- It wakes 6 times a minute; Task Coach's window thread wakes 72 to
  89 times a minute anyway (its clock for timers and reminders). It
  keeps nothing awake: a suspended laptop runs no thread.
- On a network share, a check is one small request.

watchdog, used before, reported a change at once through each
system's notices (inotify, FSEvents, ReadDirectoryChangesW), but woke
for every change to any file in the task file's folder, did not see
changes made from another computer on a network share, and differed
per system (about 6,000 lines, a compiled part on macOS). Another
program changing the open file is exceptional, and the notice only
asks (nothing is merged or reloaded unasked), so 10 s is soon enough
(**ruled by designer 2026-10-03**); every save checks the file first
anyway.

## Backups

Every overwrite of a task file keeps the file as it was, **ruled by
designer 2026-10-06** (P94, "yes proceed"): before each save
(`AutoBackup`, on `taskfile.aboutToSave`; with autosave, after each
change) and before a restore replaces a file
(`BackupManifest.restore_file()`), so a wrong restore can be restored
back. A restore that cannot keep the file does not replace it.

- **Where:** the backups folder in the user's data folder
  (`settings.backups_dir()`), one folder per task file named by the
  SHA-1 of its path, `backups.xml` mapping those to the paths; each
  backup a bz2 copy, `YYYYMMDDHHMMSS.bak`.
- **Named by when its contents were saved** (`backup_name()`: the
  file's modification time), to the second; the Backup Manager shows
  that time with its seconds. A version already kept is not copied
  again, and a copy is whole or not there: it is written beside, then
  renamed (a copy cut short, disk full or killed, is not taken for
  one). Until 2026-10-06 a backup was named by when it was replaced,
  and the Backup Manager showed it to the minute: the newest looked
  like the latest work but was the save before it, autosave's several
  a minute looked alike, and a
  restore over the file lost its latest save for good (the same in
  2.0.3.0). Backups made before keep their old names.
- **How many:** at least 3, then the natural log of the oldest one's
  age in minutes (about 7 after a day, 13 after a year); each save
  removes at most 3, each time the one closest in time to its
  neighbours, never the oldest or the newest.
- **Restore** (File > Manage backups): choose the file and a backup;
  Restore asks where (the file itself by default), keeps the file
  there as a backup, replaces it whole (`SafeWriteFile`, the
  destination locked, [FILE_LOCKING.md](FILE_LOCKING.md)) and opens
  it. Unsaved changes are offered for saving first. A backup that
  cannot be read leaves the file as it was.

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
  included (`restoring()`, as undo and redo:
  [UNDO_REDO.md](UNDO_REDO.md#architecture-snapshot-and-diff)).
  **Ruling, 2026-09-28:** the rules may
  run, as when adding subtasks in the editor, but not through a
  separate path for this fringe function; what they would change (a
  completed parent holding an open subtask from the other file) is
  left to the user.
- Deletions do not carry over: an item deleted in one file comes back
  from the other.

## Category Membership

**Asked by designer, 2026-09-29:** stored the same way in memory, in
the file and in the code: on the item that points, like a task's
prerequisites. In format 38 (release 2.0.3.0) a task's or
note's `categories` attribute lists its categories' IDs, sorted; a
note of a task, a category, an attachment or a note included. Only
categories in the file are written, so a template has none, as
before. The category node also lists its members in the file
(`categorizables`), for older releases ([Versions and
Compatibility](#versions-and-compatibility)).

Older files stored it on the category: its `categorizables` attribute
(`tasks` before tskversion 19; before 14, category nodes inside the
task nodes). The reader turns those into the items' categories, and
the next save writes the new form, next to the old one while older
releases are supported.

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

**Ruling, 2026-10-05** (GitHub #169, P205): a copied task keeps its
original's prerequisites: those copied with it as their copies, the
others as they are. At the paste each prerequisite is the file's own
item with its ID, whatever the view shows (a filter, a search) and
also after the file was closed and opened again; one the file no
longer holds (deleted since the copy, or in another file) is dropped,
and the reverse links (dependencies) are added. No task that was not
copied changes; templates, which copy through `Task.copy()` too, are
unchanged (`copies_of()`, `link_pasted()` in `command/clipboard.py`).
A copy had no prerequisites before.

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

## Versions and Compatibility

**Asked by designer, 2026-10-01:** a file this release saves opens,
as they left it, in the releases back to 2.0.2.0; a format change
reaches older releases within a window set by version, not date.

- **Backward compatibility**, older files in this release: always,
  back to the first format; the reader converts them.
- **Forward compatibility**, this release's files in older releases:
  within the window, now back to 2.0.2.0.

### Two Numbers

The `<?taskcoach?>` processing instruction holds:

- `tskversion`: the format a reader needs, like ZIP's "version needed
  to extract". Every release since 0.72.9 refuses a file whose
  `tskversion` is above its own ("created by a newer version"), so it
  goes up only when older releases would misread the file.
- `tskformat` (since 2.0.3.0): the format written, which says how to
  read it. Without it, `tskversion` is both.

`meta.data.tskformat` is the format this release writes and the newest
it reads; `meta.data.tskversion` the version it writes as needed. The
reader refuses a file needing more than `tskformat` and reads by the
file's `tskformat`.

### Changing the Format

- A field older releases ignore and whose absence is its default
  ([Defaults](#defaults)): written at once; `tskformat` goes up, so a
  file says what it holds.
- A change older releases would misread (data moved, a new meaning, a
  value they cannot take): **expand and contract**, also called
  parallel change. Expand: write the new form and keep writing the old
  one; `tskformat` goes up, `tskversion` stays. Contract, once the
  window has passed: stop writing the old form, raise `tskversion`.
  The reader keeps reading the old form, for the files saved meanwhile.
- An older release rewrites the whole file and keeps no attribute it
  does not know, so no stale new form outlives its save.
- Before a release that changes the format, and before a contract, run
  `docs/scripts/format_compat_check.py` against the oldest release in
  the window: its own file must come back unchanged from this release.

### Format 38 (2.0.3.0)

Written as `tskversion` 37, `tskformat` 38 since 2026-10-01. What is
written only for releases reading 37 is in
`persistence/xml/legacy.py`:

| Format 38 | Also written for releases reading 37 |
|---|---|
| A task's or note's `categories` ([Category Membership](#category-membership)) | A category's `categorizables`: its members in the file |
| A mail attachment: `type="mail"`, its `mid:` link as `location` ([EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md)) | `type="uri"`; read back as a mail by its `mid:` link. Not a new type: the releases refuse a whole file with a type they do not know, and read a mail from its `.eml` file |
| No selected icon (removed 2026-09-28) | `selectedIcon` as read, while the item's icon is unchanged |
| A modification date equal to the creation date left out | Written when the file stated it |

Checked 2026-10-01 against 2.0.2.0 and 2.0.2.25 with the script: their
file, saved by 2.0.3.0 and by them again, equals their first save but
for sub-second parts of dates (2.0.3.0 keeps whole seconds; they show
them alike). Saved by them, a 2.0.3.0 file loses what they do not
know: a mail's sender and sent date, an effort's creation and
modification dates, a category's style priority; and, by their own
bug, the categories of notes on attachments (P29, fixed in 2.0.3.0).

Development builds saved files as `tskversion` 38 only from 2026-09-29
to 10-01. Opening one marks it unsaved and logs it (`[FILE]`); autosave,
on by default, saves it in both forms at once. A template saved so is
saved again when the template list reads it (`[TEMPLATE]`).

### To Do: Retire the Old Forms

Since 2.0.3.0, 2026-10-01. **Review between January and April 2027**
(three to six months), and retire them once the designer rules that
2.0.2.x need not open new files:

1. Delete `persistence/xml/legacy.py` and its calls in the writer and
   the reader.
2. Write `tskversion` 38: `meta.data.tskversion` equal to `tskformat`.
3. Keep reading the old forms: a category's `categorizables` before
   format 38, a `mid:` link as a mail.
4. Drop the healing of `tskversion` 38 files (`TaskFile._read()`,
   `TemplateList._read_template()`), which no file then needs.
5. Update this section, the tests and the check script.

2.0.2.x then show "created by a newer version" for new files and lose
nothing.

### How Far Back a File Opens

Format 37 dates from Task Coach 1.3.23 (2013-02-07); 1.3.22 and older
refuse it. The format changed in 2026 without a new number, so a file
of 2.0.2.25 opens fully only back to 2.0.2.0 (2026-02-18):

- before 2.0.1.52 (2026-01-25), an icon chosen for an item raises an
  error when drawn: 2.0.2.0 renamed the icons, and older lookups fail
  on names they do not know;
- before 2.0.1.36 to 2.0.1.42 (2026-01-18 to 20), a weekly
  recurrence's weekdays, the planned duration and its mode, and an
  effort's entry mode are ignored, and dropped on their save.

`tskformat` makes such changes visible from now on.

## Related Documentation

- [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md) — Domain Attribute model,
  value normalization, setter/callback pattern
- [DATETIME_PRESETS.md](DATETIME_PRESETS.md) — Preset/propose modes and
  how they interact with persistence
- [DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md) — Duration modes,
  starting state documentation ("Start: Automatic mode")
