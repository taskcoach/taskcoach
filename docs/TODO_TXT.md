# Todo.txt (removed)

Removed 2026-10-06, **ruled by designer** ("remove the to do for now
... if ever someone asks for it again"): Export as Todo.txt, Import
Todo.txt and the automatic import and export on saving (Preferences >
Files). This page keeps what was found, for a request to bring it back.
Synchronization in general, CalDAV included: [SYNC.md](SYNC.md).

## What It Was

Added 2011 (6eeb8c640, 270036860) so tasks could be edited on Android
with Todo.txt Touch, the official [Todo.txt](https://github.com/todotxt/todo.txt)
app, which read the file from Dropbox; Task Coach has never had a
phone app.

- Export wrote one line per task: priority 1 to 26 as `(A)` to `(Z)`,
  `X` and the completion date, the planned start date, the subject with
  its parents (`Parent -> Child`), the categories whose subject starts
  with `@` (contexts) or `+` (projects), `due:` and the due date,
  `tcid:` and the task's ID. Dates only.
- A context or project is one word, so a category was written with its
  parents joined by `->` and spaces as underscores: `@Contexts
  (GTD-Style) -> @Errands` became `@Contexts_(GTD-Style)->@Errands`.
- Import read such lines; contexts and projects became categories, as
  Task Coach keeps one parent per task and Todo.txt allows several
  projects.
- Automatic import and export: each save first imported `name.txt`
  beside `name.tsk`, then wrote it again; opening the task file
  imported it too. `name.txt-meta` kept the lines as written, to find
  the lines edited elsewhere and the tasks deleted there.

The last release with it: 2.0.3.0, tag `v2.0.3.0`
(`taskcoachlib/persistence/todotxt/`,
`persistence/autoimporterexporter.py`, the export dialog, the menu
items and the Preferences options). Before the removal a fix (P241)
made a re-import read an edited line back as it was written: the
categories with spaces, a category deleted in Task Coach, the times
of the dates; it is not in that release.

## Why It Was Removed

Analysed 2026-10-06 (To Do 29 in
[REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md)):

- Todo.txt Touch left the stores in 2017, when Dropbox closed the API
  it used; it was archived in 2020.
- The file broke the format for completed tasks: `X` in capitals and
  after the priority, where the format wants a lowercase `x` first; and
  the planned start date where the format has the creation date. Other
  apps showed tasks completed in Task Coach as open. Reported 2016
  (SourceForge #1632), never fixed.
- Reports: four on SourceForge (#1087, #1274, #1446, #1632, 2012 to
  2016), none on GitHub.
- Data loss, the same on 2.0.3.0: with automatic import on, a task
  whose line was gone from the `.txt` file was deleted at the next
  save, with its efforts, and Undo could not bring it back. Todo.txt
  apps archive completed tasks by moving their lines to `done.txt`;
  an emptied file deleted every task.
- In 2.0.3.0 every import added a copy of each category with a
  space in its name (the underscores were not read back), a category
  deleted in Task Coach came back, and an edited line lost the times
  of its dates.
- Todo.txt has no times, notes, efforts, attachments, recurrence or
  real subtasks: a sync through it loses data by design.
- About 820 lines of code and 730 of tests.

## The Format in 2026

Alive in a niche (checked 2026-10-06):

- Android: Simpletask (a Todo.txt task manager; versions for a local
  file, Nextcloud, any WebDAV server, and Dropbox outside F-Droid),
  Markor (a text editor with a Todo.txt mode, updated March 2026).
- Desktop: sleek (Windows, macOS, Linux), `todo.txt-cli`.
- iOS: SwiftoDo.

None of them syncs tasks itself: each edits one text file that a file
sync (Dropbox, Nextcloud or WebDAV, Syncthing) copies between devices;
edits made on two devices at once leave a "conflicted copy" to merge
by hand. None speaks CalDAV.

## To Bring It Back

Restore it from the tag `v2.0.3.0`, then:

- Redo P241's fix (above).

- Write the format as specified: a lowercase `x` first, the priority
  kept as a `pri:` tag on completed tasks, the planned start as a tag
  (Simpletask reads `t:`), the creation date where the format puts it.
- Never delete a task because its line is gone: archiving moves lines
  to `done.txt`. Read `done.txt` as completions, or ask before
  deleting, and make it undoable.
- Read back a context or project removed elsewhere (it stayed on the
  task, and the next export wrote it again).
