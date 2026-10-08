# Exports

File > Export > Export as HTML, as CSV and as iCalendar. HTML and CSV
export tasks, efforts, categories, notes and attachments; iCalendar
tasks and efforts.

1. [What Is Exported](#what-is-exported)
2. [HTML](#html)
3. [CSV](#csv)
4. [iCalendar](#icalendar)
5. [Where the File Goes](#where-the-file-goes)
6. [Open Problems](#open-problems)

## What Is Exported

The dialog's "Export items from" says which items are written:

- **An "(All)" choice** ("Tasks (All)", "Effort (All)", ...): every
  item of the type in the file, whatever the views filter, in one flat
  list ordered as a new view of the type orders it (its defaults in
  `config/defaults.py`): tasks by status, then due date; efforts by
  period, newest first; categories and notes by subject, ignoring
  case. Until 2.0.3.2 they came in the file's own order, a different
  one at each export. Code: `persistence/allitems.py`.
- **An open view**, shown as "Tasks (3 selected)": the rows selected
  in that view, in its order and with its filters. A whole view is
  exported by selecting all its rows first (Edit > Select All).

HTML and CSV offer the columns of the first open view of the type, or
of a hidden one; an "(All)" choice ticks them all. iCalendar offers
its fields instead.

Each column holds what its view's column shows (a task's priority,
its subtree values: [TASK_FIELDS.md](TASK_FIELDS.md)), with dates
written out where a view says "Today" and every effort's period in
full; an attachments column lists the attachments' subjects. A date
not set is written blank, and left out of iCalendar
([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#dates-not-set-is-the-latest-date)).

## HTML

- Every cell is escaped.
- Rows in the items' colours, as the views draw them
  ([APPEARANCE_STYLES.md](APPEARANCE_STYLES.md#what-the-views-draw)).
- The style information is in the page, or by the dialog's choice in
  a CSS file beside it, written only when missing so that changes to
  it stay.

## CSV

- UTF-8 with a byte order mark, which Excel needs to read it as UTF-8.
- Dates and times in one column, or by the dialog's choice in two.
- Import CSV reads it back; how its dates are read:
  [DEPENDENCIES.md](DEPENDENCIES.md#python-dateutil-to-do-89).

## iCalendar

- Tasks as `VTODO`, efforts as `VEVENT`, lines ending in CRLF.
- A task's categories: its own and inherited
  ([CATEGORIES.md](CATEGORIES.md#own-and-inherited-categories)).
- `PRIORITY`: the task's own priority, plus one, capped at 3
  ([TASK_FIELDS.md](TASK_FIELDS.md#priority)).
- The format a CalDAV server keeps tasks in
  ([SYNC.md](SYNC.md#caldav)).

## Where the File Goes

The folder each export dialog opens in:
[FILE_DIALOGS.md](FILE_DIALOGS.md). The Flatpak's access to it:
[FLATPAK.md](FLATPAK.md#file-access-and-the-file-chooser-portal).
Export as Todo.txt was removed: [TODO_TXT.md](TODO_TXT.md).

## Open Problems

- **"Attachments (All)" writes no attachment.** It is the choice the
  HTML and CSV dialogs start on; the file has the header row only, as
  `all_items()` has no attachment list, nor had the writers' own lists
  before it. **Parked by designer 2026-10-08** ("we will wait till
  someone asks for it and they explain exactly what they want").
- Recorded in [REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md):
  - P190: CSV cells starting with `=`, `+`, `-` or `@` run as
    formulas in a spreadsheet ([Security](REFINEMENT_REFACTOR.md#security)).
  - P193: iCalendar TEXT values are not escaped
    ([Security](REFINEMENT_REFACTOR.md#security)).
  - P207, in part: a selection-only export scans the whole view for
    each item ([Performance](REFINEMENT_REFACTOR.md#performance)).

Tests: `tests/unittests/persistenceTests/` (`AllItemsTest.py`,
`HTMLWriterTest.py`, `CSVWriterTest.py`, `VCalendarWriterTest.py`).
