# Changelog

What changes for users in each release, newest first. A release's
section is the text of its GitHub release page
([PACKAGING.md](docs/PACKAGING.md#release-notes)).

## 2.0.3.0

### Faster

- Task statuses, reminders and the views follow the clock at almost
  no cost: an idle file of 2,000 tasks took a quarter of a second
  every second, and now one short pass a minute; while many statuses
  change, the window stays responsive.
- A large file opens about twice as fast with less memory; sorting a
  tree view of 2,000 tasks takes 0.6 s instead of 3.5 s, and a filter,
  search or tree/list switch is faster too; a file of 2,050 late tasks
  froze Task Coach for a minute when opened.
- Closed editors, Preferences and floating views no longer stay in
  memory.

### Files, saving and undo

- A file another program changed is never replaced unasked: Task
  Coach checks the open file every 10 seconds on every system, network
  shares included, and asks whether to reload it or merge its changes.
  Preferences > Files no longer has "Use polling for file monitoring".
- File > Merge combines two files, keeping the newest copy of each
  item; nothing is merged automatically.
- Undo and redo restore exactly what each action changed, and undoing
  back to the saved state clears the unsaved mark. Changes Task Coach
  makes itself (a status changing with the time) no longer mark the
  file unsaved, and opening a task's editor no longer changes a file
  just saved.
- Files saved by this version open in the earlier 2.0.2 releases.
- Categories given in a task's editor with Check all and Uncheck all,
  and those of pasted notes and of attachments' notes, were lost on
  save; they are kept.
- Items with the same ID in a file are separated when it is read, with
  a message; cut and paste keeps an item's identity.
- New items' IDs no longer contain the computer's network address.
- Text holding characters a task file cannot store (control
  characters pasted from another program) no longer makes the file
  impossible to open, and Help > Anonymize writes a file Task Coach
  can open.
- Opening the editor of a task that has recurred no longer marks the
  file changed and resets the task's recurrence count; changing the
  recurrence keeps the count too, so "Stop after N recurrences"
  counts the recurrences already made.

### Tasks, categories and efforts

- Sorting by the Status column sorts by status; it sorted by subject.
- A fee typed in the task list is stored as typed ("12.5" became
  0.50); the Budget cell accepts typing; a % complete or priority
  typed in the list is kept when you click elsewhere.
- In the Adjust due date mode, a due date changed in the task list is
  kept when the start then changes in the editor.
- Pasting several notes in a task editor adds them all.
- A task with subtasks shows its status icon.
- The effort view's rows, period totals and Task and Categories
  columns follow changes at once; decimal time, the calendar's week
  start and its gradient apply at once.
- A calendar saved in month view no longer stops Task Coach from
  starting.
- A reminder window follows its reminder changed elsewhere and closes
  without snoozing when its task is deleted or completed.
- Undo after changing % complete of several tasks says what it undoes.
- On Linux, New effort in the tray menu opens the effort editor; it
  did nothing.

### Lists, editors and keyboard

- Editing cells in place is off by default, after an upgrade too;
  Preferences > Features > Edit cells in place turns it on, and Edit
  in place with a slow double click opens a cell only on a slow double
  click.
- An in-place edit box closes and saves when another view becomes
  active; a right-click in it acts on the box, and the list takes keys
  again after Enter or Escape.
- The selection stays where it was after a sort, a filter, a search or
  a drag and drop; collapsing a parent of a selected task updates the
  status bar and buttons.
- Ctrl+PgDn and Ctrl+PgUp switch views wherever the focus is; View >
  Activate next and previous viewer work, and making another view
  active no longer freezes the window.
- Ctrl+Z and Ctrl+Y in the search box and in text fields undo the
  typing, not task changes; Enter in the search box no longer opens
  the selected task's editor; Ctrl+Enter in the task tree marks the
  task completed instead of opening it; Ctrl+Shift+A is Deselect All
  only.
- A shortcut works even if its menu last showed it disabled (Ctrl+S
  after the File menu was opened with nothing to save).
- A held key no longer opens a pile of editor windows.
- Showing or hiding a column keeps each row's icons in their columns,
  and a column of icons fills at once; "Hide this column" works
  wherever its menu item lies.
- Tooltips hide when an editor opens and after Expand all or Collapse
  all.

### Import, export and mail

- Dropping an e-mail from Thunderbird, Evolution or Claws Mail, or a
  file from a file manager, attaches it again. Where no keychain can
  store the mail password, Task Coach asks for it once until it quits,
  without an error message asking for a bug report; a mail server
  offering NTLM no longer gives an error.
- File > Import > CSV works again. It has an Encoding choice, set to
  the guessed encoding: a file that shows garbled in the preview
  (Central European and Turkish files on most systems) imports right
  once its encoding is chosen. It reads month names and AM/PM in the
  system's language as well as English; a date without its day or
  month imports empty instead of taking today's (a missing year is
  still this year); "Due: 2026-10-05" is year-month-day with day first
  chosen; a number too long to be a date no longer stops the import.
- Template dates such as "2 days before sunday" or "2 days after last
  sunday" give the right day; they went the wrong way. Weekday names
  are English on every system, as the Help says: on other systems
  "next saturday" was refused and templates using weekday names were
  missing from New task from template.
- On Linux and macOS, starting Task Coach with `--ini` no longer moves
  your templates to a `templates-old` folder, out of New task from
  template. Templates already moved can be brought back with File >
  Import template.

### Languages

- French, Spanish and Portuguese (Portugal and Brazil): the task,
  category and effort views, editors, menus and file messages no
  longer show texts in English.
- The language from the environment follows the usual order: LC_ALL,
  then LC_MESSAGES, then LANG.
- With a settings file given with `--ini`, dates, times and amounts
  follow its formats.

### Removed

- The Dependency Graph view: no install provided the library it
  needed.
- The window options "Start with the main window iconized", "Hide main
  window when iconized" and "Minimize main window when closed".

### Packages

- The Ubuntu 22.04 package installs: Task Coach no longer needs
  pyparsing 3.
- The Debian, Arch and Fedora packages install PyGObject, which the
  tray icon needs on desktops using AppIndicator.
- Task Coach no longer needs pypubsub, lxml, watchdog, pyxdg, distro,
  numpy, WMI, pyparsing or six; the Windows installer is 16 MB
  smaller.
- The setup scripts for running from source finish, and install spell
  checking.
