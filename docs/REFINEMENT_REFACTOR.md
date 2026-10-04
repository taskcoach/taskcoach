# Refinement Refactor

What the master scheduler refactor leaves open, carried forward for a
refinement and cleanup pass after the release, **asked by designer
2026-10-04**: "carry forward the open issues to a new ... refactor task
that's refinement cleanup rather than a major cleanup". Details stay
where each item was recorded; this list only orders them.

## To Do

The one list for this refactor, numbered in the order found; an item
is crossed out and cut to a stub when done or decided, and new items
go at the end.

1. Task statistics view: draw it in Task Coach's own code instead of
   `wx.lib.agw.piectrl`, whose paint loop keeps a core busy
   ([TASK_STATISTICS.md](TASK_STATISTICS.md#to-do) 1).
2. Renames too wide for the PEP 8 pass of 2026-10-04, each its own
   comprehensive change ([PEP8_MIGRATION.md](PEP8_MIGRATION.md)):
   `selectionOnly` and the other export writer parameters (60 uses),
   `foregroundColor`/`backgroundColor` (45), `modificationEventTypes`
   (48), the sort interface (`sortBy`, `sortKey()`,
   `isSortCaseSensitive()`, `sortCaseSensitive`, and the
   `<key>SortFunction`/`<key>SortEventTypes` names the sorter builds
   from the column name), `onSelect` (36), and the editor tests' hooks
   `getItems`/`createTasks` (39); with D1's below.
3. Plain dialogs placed by wxGTK's deferred first show: the IMAP
   password dialog and once the Tip of the day map at the screen's
   top-left, squashed (P178 in
   [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues));
   the editors' workaround
   ([WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md#first-show-on-wxgtk)) for
   every dialog.
4. Prototyped 2026-10-04, ruled low value then (rarely used):
   - P170, template dates read in part: the templates dialog accepts a
     date only when all its text is read
     (`timeexpression.parse(value, whole=True)`); saved templates read
     as before.
   - P57, Norwegian systems get British or C dates: the workaround
     only on Windows, where the date picker it was for is native.
   - To Do 82, the Windows and macOS builds' Python 3.11.9 has Expat
     2.6.0: build both on Python 3.13 (3.13.16 has Expat 2.8.5;
     wxPython 4.3.1, pywin32 312 and py2app 0.28.10 support it), and
     a build check that Expat is 2.7.2 or later.
5. `dbus-python` to Gio (To Do 92 in
   [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#to-do)),
   after the research it lists.
6. The open pre-existing issues of
   [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues),
   each still to rule: P65 (code only tests use), P69 (Python 2 style),
   P70 (stale comments), P71 (pylint leftovers), P76 (unused image
   folders), P77 (three AppStream files), P84 (build inputs adrift),
   P85 (no CI job runs the tests), P86 (old CI actions and images),
   P91 (editors first open cut off), P92 (fit editors and floating
   panes to the monitors), P93 (editor layout saved but not loaded),
   P94 (planned in TODO.md), P96 (toolbar jitter), P97 (dates tied
   against the duration modes), P98 (date and time refactors), P100
   (list selection; the effort and attachment views select the row
   below a deleted one), P101 (link colour), P103 (toolbar sentinels),
   P104 (long-term migration items), P106 (geometry checks on LXDE),
   P109 (editor shortcuts against translations, relative date
   presets), P110 (IMAP OAuth2 and NTLM), P112 (stale doc text), P125
   (Windows display scale factors), P138 (Windows tree scrollbars),
   P159 (AppImage tray), P162 (focus after a click in a floating
   view), P176 (macOS spelling).
7. Test suite, fixed as found without a ruling: P63 (the translation
   coverage tests read a stale template) and P90 (a test file now and
   then fails to start).
8. The texts still in English outside the core screens in French (223),
   Spanish (262), Portuguese (235) and Brazilian Portuguese (257):
   mostly Preferences (146), then sounds, the CSV import, the tray and
   the views other than tasks, categories and efforts; the core ones
   were translated 2026-10-04 (To Do 100 in
   [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#to-do)).

## Low Priority, Deferred

The Deferred and Will Not Do items of the master scheduler refactor,
**asked by designer 2026-10-04**: out of that refactor's scope, open
here at low priority. Details under their numbers in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#deferred-and-will-not-do).

- D1. The renames too wide for that refactor: domain and viewer
  methods (`addChild`, `removeChild`, `computedStatus`,
  `processReminder`, `onSelect`, `_createColumns`,
  `subjectImageIndices`, `registerObserver`, `removeObserver`) and
  keyword families (`taskList`, `effortList`, `cssFilename`,
  `selectionOnly`).
- D2. The GTK warning at every launch, from inside GTK.
- D3. Attachment styling.
- D4. One base class for the two tray icons (different by design).
- D5. The Plasma window management protocol on KDE Plasma Wayland,
  for users there to test.
- D6. The `wx.Display` replacement on Windows, for users there to
  test.
- D8. What cannot be tested here: Windows, macOS, Wayland, KDE and
  Flatpak items.
- D9. Retire the forms written for releases reading `tskversion` 37,
  between January and April 2027.
- D10. The Task statistics view's busy repaint loop (To Do 1 above).
- D11. Dark theme colours: only on the designer's request.
- D12. The reminder sound's player process left running unwatched.
- D13. `squaremap` kept as a dependency, not copied.
- D14. The Calendar view's `invalid bitmap size` log line.
- D15. Text cut without "..." in too-narrow list columns.
- D16. Empty Papirus icon folders and monochrome icons.
