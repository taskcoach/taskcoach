# Changelog

What changes for users in each release, newest first. A release's
section is the text of its GitHub release page
([PACKAGING.md](docs/PACKAGING.md#release-notes)).

## 2.0.3.0

- On Linux, New effort in the tray menu opens the effort editor; it
  did nothing.
- Opening the editor of a task that has recurred no longer marks the
  file changed and resets the task's recurrence count; changing the
  recurrence keeps the count too, so "Stop after N recurrences"
  counts the recurrences already made.
- File > Import > CSV has an Encoding choice, set to the guessed
  encoding: a file that shows garbled in the preview (Central European
  and Turkish files on most systems) imports right once its encoding
  is chosen.
- File > Import > CSV reads month names and AM/PM in the system's
  language as well as English; a date without its day or month
  imports empty instead of taking today's (a missing year is still
  this year); "Due: 2026-10-05" is year-month-day with day first
  chosen; a number too long to be a date no longer stops the import.
- Editing cells in place is off by default, after an upgrade too;
  Preferences > Features > Edit cells in place turns it on.
- Preferences > Files no longer has "Use polling for file monitoring":
  Task Coach checks the open file every 10 seconds on every system,
  network shares included, and asks when another program changed it.
