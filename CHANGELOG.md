# Changelog

What changes for users in each release, newest first. A release's
section is the text of its GitHub release page
([PACKAGING.md](docs/PACKAGING.md#release-notes)).

## 2.0.3.5

### Editors

- Markdown preview: a Preview button under the Description label of
  tasks, notes, categories and attachments, and beside Close in the
  effort editor, shows the description formatted: headings, bold,
  italic, lists and task lists, code, quotes, tables and links, as
  written by hand or pasted from GitHub or an AI chat. A second click
  goes back to editing. The text is saved as typed, and each item
  remembers whether its preview was showing; releases before this one
  show the text as typed.

## 2.0.3.4

### Editors

- Clicking into another field of a window removes the text selection
  of the field left, on every platform: a Subject or Description box
  kept showing its selected text, which looked as if it still had the
  focus.

### Windows

- With "Let the system determine the language", Task Coach starts in
  the language of the Windows regional format again, with its date
  format and spell checking language; since 2.0.0.101 it started in
  English.
- The date fields of the editors show the date format of
  Preferences > Regional, as the lists do; they showed Windows' own.

## 2.0.3.3

### Appearance

- Preferences > Statuses > Appearance flow: where the icon, colours
  and font of an item without its own come from. From categories and
  tasks (as before), from categories only, from tasks only, or none:
  each item then shows only its own style and a task its status.
- The "No icon" icon override works: the item shows no icon, and the
  icon of its categories or parent task no longer shows through. Its
  subtasks show their own icons. Picking "No icon" used to untick the
  override, so the inherited icon stayed. Releases before this one
  show the inherited icon for such an item.

## 2.0.3.2

### Export

- An "(All)" choice of Export as HTML, CSV or iCalendar writes the
  items in the order a new view sorts them: efforts by period, newest
  first; tasks by status, then due date; categories and notes by
  subject. They came in a different order at each export.

### About

- A normal release: the About page shows "Version 2.0.3.2", no longer
  followed by "alpha".

## 2.0.3.1

### Tasks

- Copied tasks keep their prerequisites: tasks copied together wait for
  each other's copies, as the originals do, and for the same other
  tasks. A copy used to have no prerequisites.

### Mail

- Task Coach no longer connects to mail servers or asks for mail
  passwords: a dropped mail is read only from what the mail program
  hands over. A Thunderbird mail is attached when Thunderbird hands
  over the mail itself (on Wayland, or when several mails are dragged
  on Linux), and on X11 one mail too, its file asked of Thunderbird
  (not in the AppImage, which lacks PyGObject); when it gives only the
  mail's address, a message says to save the mail as a file and drag
  the file. Such a drop used to log in to the mail server, or attach
  an empty or wrong mail.
- Mail sends a task's whole subject to the mail program: a subject
  with `&` or `#`, such as "R&D review", arrived cut ("R"), and with
  `#` the body was lost. On macOS these two characters become `_`.
- When a mail program refuses Mail's new message because it has no
  recipient, the message opens addressed to `recipient@example.com`,
  an address reserved for examples that accepts no mail: sent
  unchanged, it bounces. It used to be `recipient@domain.com`, a
  company's domain whose mail is delivered, and it replaced the
  recipients a task's description names. Any other failure is shown.
- Mail of several tasks puts a blank line between them; each
  description used to end in stray line-break characters.

### Efforts

- A task's editor shows all the efforts of the task and its subtasks,
  whatever categories are ticked, as it shows all its notes and
  attachments: an effort added there no longer stays hidden.
- One task is tracked at a time. Start tracking takes one task, and a
  new effort, or one given no stop in its editor, ends the tracked
  one; a copied effort is no longer tracked.
- The Idle time notice keeps working on GNOME when GNOME Shell
  restarts (on X11); it stopped until Task Coach was restarted. On
  GNOME Wayland it now works on every Linux package but the AppImage
  (Arch used to need python-dbus, installed only on request). A
  desktop that does not answer holds Task Coach at most a second, not
  25.

### Lists

- After a click in a floating view (a view dragged out of the main
  window), the keys go to that view. They went back to the main
  window's list, so Delete could act on a task selected there.
- A change that moves a task in the list, such as Mark completed,
  moves its row instead of rebuilding the whole list: with 2,000 tasks
  the window no longer stops for 0.7 s.
- After a delete, every view keeps the selection on the same line, as
  most programs do: the row that moves into the deleted one's place,
  or the row above when the last row went. The task, category and note
  views used to select the row above.
- The effort and attachment views keep the selected item selected when
  rows are added above it or the view is sorted; the highlight used to
  move to another item.
- Columns can be moved: drag a column's header sideways and a line
  shows where it will land, before the first column, between two or
  after the last. Each view keeps its order, a hidden column comes back
  at its place, and a task tree's hierarchy follows the subject column.
  A click on a header still sorts, now at the release. On Windows the
  effort and attachment views, Windows' own lists, keep their order.
- In list mode the task rows start under their header's text; they
  kept the room of a tree's expand buttons.
- The lists have no rounded frame of their own inside their pane's.

### Editors

- An editor opened for the first time shows its pages whole, the task
  editor's dates and priority included, instead of a 400x300 window
  that cut them off. On a small screen it takes at most 80% of the
  screen less its panels, title bar and buttons on screen; the pages
  scroll. A size you give an editor is kept, as before.
- An editor reopens with its tabs as you arranged them, moved or split
  side by side, as in the 1.x releases; since 2.0 only the active tab
  came back.

### Dialogs

- On Linux, a dialog opened after another window closed, or at start
  (the Tip of the day), opens whole and in its place: centred on Task
  Coach's window, a reminder on its screen. It could open at the
  screen's top-left with its last lines cut off, such as the Tip of
  the day's "Show tips on startup".
- Every file dialog but Restore backup's opens in the folder last
  chosen in one of its kind (task files, each export, each import),
  else in the open task file's, else in Documents. Import CSV, Import
  template and Add attachment opened in the folder Task Coach was
  started from, on Windows its program folder; the exports stayed in
  the old folder after a Save As elsewhere. Attachments still remember
  their folder between sessions.
- The Backup Manager's window is titled "Manage backups"; its title
  bar was blank.
- Preferences keeps every change until OK or Apply, and Cancel drops
  it. Durations' Add and Delete and the Theme page's colours used to
  be saved at once and kept after Cancel. Apply is greyed until
  something changes, and again after it.
- Preferences > Theme: unchecking System for "Other Months Days
  Background" shows the colour then used; it kept showing the
  system's.

### Screens

- Every window opens whole on a screen, so that after a change of
  monitors Task Coach can always be seen and moved. Its window, saved
  partly off screen, across two screens or on a screen that is gone,
  opens centred on the screen it was most on, or on the main screen
  when most of it was on none. It used to stay partly off screen
  while its title bar showed, or open at the edge of the nearest
  screen.
- A floating view opens on the screen of Task Coach's window, as
  editors do: saved elsewhere, or partly off that screen, it opens
  centred on the window. It used to open where it was saved, even on
  a screen that is gone.
- On Linux, a floating view opens above Task Coach's window; at some
  starts it opened behind it, out of sight.
- A window larger than its screen opens at 80% of it, centred. Task
  Coach's window used to fill the screen, and an editor was placed
  and sized by the system.
- Every dialog opens within 80% of the screen, centred, its contents
  scrolling: Preferences, Help, About, License and the Backup Manager
  could fill a small screen, Preferences at least 1250 pixels wide.
  The icon picker is a little taller (80% of the screen, was 75%).

### Backups

- Restoring a backup over a task file first keeps the file as a
  backup, so a restore can be undone. A restore used to lose the
  file's latest saved version for good.
- File > Manage backups lists each backup with the time its contents
  were saved, to the second. It showed when the backup was replaced,
  to the minute: the newest backup was the save before the latest,
  and autosave's backups of a same minute looked alike.

### Tray

- The Linux tray menu no longer holds Task Coach for seconds after each
  change to a large file's tasks: it changes only what changed, about
  15 ms with 2,000 tasks instead of 1.7 to 2.4 s.
- The tray menu's task icons follow the tasks: a task turned overdue
  shows so. They stayed as they were until a task was added, renamed
  or completed, and the first menu after opening a file had none.

### Starting

- Task Coach's window appears at once, and the file opens in it. With
  a large file the window used to stay blank, or black, until the
  file was read.
- While a task file opens or merges, the pointer shows busy and the
  status bar says so; the status bar used to say "Closed".
- The task list appears once, complete with its colours and icons;
  its rows used to appear plain and take their colours a second or
  two later. Opening a large file is faster: with 2,000 tasks 1.1 s
  instead of 1.8 s.
- The tray icon appears once the file is open, its menu complete.

### Settings and quitting

- Settings, Preferences included, and the window's layout and size are
  saved while Task Coach runs, not only when it quits: a logout, a
  shutdown or a crash no longer loses them. The settings file is
  replaced in one step, so a crash or power cut never leaves it empty.
- A saved task file is on disk before it replaces the old one, so a
  power cut right after a save leaves the old file or the new, never
  an empty one.
- Told to end by the system (a shutdown, a restart, `kill`), Task
  Coach saves the open file without asking and quits, instead of
  waiting on "Save changes?" that nobody can answer.

### Removed

- Todo.txt: Export as Todo.txt, Import Todo.txt and the automatic
  import and export on saving (Preferences > Files). Made for the
  Todo.txt Android app, withdrawn in 2017; with automatic import on, a
  task whose line another app removed from the `.txt` file was deleted
  with its efforts. Existing `.txt` files are left as they are; CSV and
  iCalendar remain for exchanging tasks.
- Spoken reminders: "Let the computer say the reminder" (Preferences >
  Reminders, Linux and macOS). With it on and no espeak program, which
  Debian and Ubuntu do not install, a reminder did not show at all.
  Reminders still show and play their sound.

### Packages

- Task Coach no longer needs keyring; the AppImage and Flatpak hold
  about 19 MB less.
- Task Coach no longer uses dbus-python (python3-dbus): PyGObject,
  which it already needs, makes its D-Bus calls. The Flatpak no longer
  asks to talk to the desktop's screen saver.
- The Flatpak may use the network, for the start-up check for a new
  version only: it failed there at every start, so the Flatpak's users
  were never told of a new release.

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
