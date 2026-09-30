# Master Scheduler Refactor

Plan to replace the full scan `MasterScheduler` runs every second.
[SCHEDULERS.md](SCHEDULERS.md) describes the scheduler as it is.

**Status:** items 1 to 33 done or decided, 2026-09-28
([Cost After](#cost-after)); what is left: [To Do](#to-do).

## To Do

The one list for this refactor, numbered in the order found; an item
is crossed out and cut to a stub when done or decided, and new items
go at the end. Details live in the sections and documents linked.

1. ~~Whole seconds everywhere: done, only logs keep fractions.~~
   [Time Resolution](#time-resolution)
2. ~~One "not set" for every task date: done, the latest date; a
   running effort's missing stop stays `None`, outside the list.~~
   [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#dates-not-set-is-the-latest-date)
3. ~~No event for an unchanged value: done (`Attribute.set()`), a
   quarter of the tick.~~ [Cost Before](#cost-before)
4. ~~Task dates and reminder on the Publisher, the reminder an
   `Attribute`: done.~~ [Why Nothing Is Missed](#why-nothing-is-missed)
5. ~~The master timer list: done, a heap, the check each second, the
   full loop at its entries, the check mode
   (`TASKCOACH_SCHEDULER_CHECK=1`).~~ [Cost After](#cost-after)
6. ~~Changes the loop reads push the current second, parents first:
   done.~~ [Data Changes](#data-changes)
7. ~~One status: done, styles and status bar counts read
   `computedStatus()`.~~ [TASK_STATUS.md](TASK_STATUS.md#migration-path)
8. ~~SyncML leftovers (sync status flags): removed.~~
   [PYTHON3_MIGRATION_4.md](PYTHON3_MIGRATION_4.md#backwards-compatibility)
9. ~~Merging ignored the actual start: done, then moot (item 13).~~
10. ~~Reminder windows when a file opens: decided, no change.~~
    [REMINDERS.md](REMINDERS.md#overview)
11. ~~UI thread busy while statuses change: done, computed values mark
    nothing unsaved and a save no longer reads the file (98% to
    11%).~~ [Cost After](#cost-after)
12. ~~Modification date on every stored change: done.~~
    [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)
13. ~~Merging: done, no automatic merge; File > Merge a union by newest
    copy.~~ [PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)
14. ~~Unsaved mark from saved data only: done.~~
15. ~~A file changed on disk: done, never replaced unasked.~~
    [PERSISTENCE_XML.md](PERSISTENCE_XML.md#saving)
16. ~~Undo back to the saved state clears the unsaved mark: done.~~
    [UNDO_REDO.md](UNDO_REDO.md#persistence)
17. ~~View state and category ownership: decided, filter and expanded
    state set no date, the task owns its categories.~~
    [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)
18. ~~Every signal on the Publisher: done, pypubsub removed.~~
    [PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#migration-log)
19. ~~The loop's hook lists what the loop reads: done.~~
    [Data Changes](#data-changes)
20. ~~Attachments re-sorted: done.~~
21. ~~A timing-dependent `EffortViewerTest` case: done.~~
22. ~~Merge ran the parent rules: done.~~
    [PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)
23. ~~`.delta` files: decided, ignored.~~
    [PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)
24. ~~The effort list took a merged file's efforts: done, it compares
    identity.~~
25. ~~Status bar counts ignored the clock: done.~~
26. ~~Object identity: decided, one object per ID within a file, the
    file to merge held apart.~~
    [PERSISTENCE_XML.md](PERSISTENCE_XML.md#merging)
27. ~~Recursive priority in the loop: decided, no; by events, as it
    always did.~~
    [TASK_FIELDS.md](TASK_FIELDS.md#priority)
28. ~~Recurrence changes reached only the subtask: done.~~
    [TASK_FIELDS.md](TASK_FIELDS.md#subtree-values-in-other-columns)
29. ~~Duplicate IDs in a file: done, corrected when read, with a
    message.~~ [PERSISTENCE_XML.md](PERSISTENCE_XML.md#duplicate-ids)
30. ~~Cut and paste changed identity: done, the first paste after a cut
    is a move.~~ [PERSISTENCE_XML.md](PERSISTENCE_XML.md#ids)
31. ~~IDs carried the network (MAC) address: done, random UUIDs.~~
    [PERSISTENCE_XML.md](PERSISTENCE_XML.md#ids)
32. ~~The unused file GUID: removed.~~
33. ~~Version: 2.0.3.0.~~
34. The undo log as object versions keyed by the modification date:
    step 1 done, steps 2 to 5 open
    ([UNDO_REDO.md](UNDO_REDO.md#todo-one-undo-log), option C).
35. ~~The views on the effective styles, the legacy styles removed~~
    ([Views on the Effective Styles](#views-on-the-effective-styles)).
36. ~~Pages drawn over the editor's tabs~~
    ([AUI.md](AUI.md#page-painted-over-the-tabs)).
37. ~~Base and effective fields beside the 14 core fields~~:
    postponed, not load-bearing for this refactor
    ([TASK_FIELDS.md](TASK_FIELDS.md#postponed-base-and-effective-fields)).
38. ~~`Timestamp.now()` always later than the one before~~: removed,
    it returned made-up times; the dates are the clock's
    ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#ids)).
39. ~~Renames deferred as too wide~~: done, the task date setters,
    `set_parent()` and `set_task()` ([PEP8_MIGRATION.md](PEP8_MIGRATION.md)).
40. ~~Signal cleanup~~: subscriptions end with their window, toolbar,
    menu or editor page; the guards that became unreachable are gone,
    the others guard delayed calls and destruction
    ([PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#signaling-system-cleanup)).
41. ~~Editor text fields save on leaving the field~~: by design, not
    an issue ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#todo)).
42. The designer's desktop test of the branch, from one consolidated
    test list.
43. Squash to one commit when the designer says the pull request is
    ready (pushes before that keep the full history), version 2.0.3.0
    in the body; the release date (2026-09-28) may move.
44. ~~A traceback lost on 2026-09-28~~: both candidates fixed, the
    spell check's timer (53) and the date popup (P12); reopen if it
    shows again.
45. Incremental pass: at a due second, process only what changed and
    what depends on it, each object once, not every object; analysis
    verified 2026-09-29 (it can match the full loop exactly), with 57;
    to decide ([Incremental Pass](#incremental-pass)).
46. ~~Status-first sort re-sorts on the clock's status changes~~: once
    after the loop's pass ([TASK_STATUS_SORT.md](TASK_STATUS_SORT.md#re-sorting)).
47. ~~Effort viewer's Task and Categories columns refresh~~.
48. ~~Decimal time applies at once~~ (`settings2.changed`).
49. ~~Calendar week start and gradient apply at once~~; the gradient
    drawer failed to paint under wxPython 4 and is fixed.
50. ~~Effort rows and period totals refresh on a stop change~~: they
    did not, on master either.
51. ~~Empty event type~~: gone, and `removeObserver()` reads only None
    as "any".
52. ~~Priority as it was~~: the effective priority of 2026-09-28
    undone, with 37 ([TASK_FIELDS.md](TASK_FIELDS.md#priority)).
53. ~~Deferred calls that can outlive their window~~: all through
    `patterns.later` ([DEFERRED_CALLS.md](DEFERRED_CALLS.md)).
54. ~~Lazy teardown~~: nothing stopped on close or quit; the timers
    freed after the event loop
    ([DEFERRED_CALLS.md](DEFERRED_CALLS.md#end-of-life)).
55. ~~Renames deferred as too wide~~: moved to
    [Deferred or Will Not Do](#deferred-or-will-not-do), D1.
56. ~~The macOS editor poll~~: removed 2026-09-29, **ruled by
    designer**. Its cause (Task Coach bug 1438, 2013): wxPython 2.8's
    Carbon port sent a synthetic Cancel that hid a background editor
    without a close event; that code left wxWidgets in 3.1, and Escape
    now closes an editor through `Close()` on every port. To check on
    a Mac: two editors, Escape twice, both close and save.
57. The master timer list keeps stale seconds: its entries carry no
    task, so a changed date's old seconds cannot be removed and a date
    not set gives seconds never reached. **Reopened by designer
    2026-09-29**: the stopgap rebuild does not solve it and points to
    a structural problem; to design with 45
    ([Stale Entries](#stale-entries)).
58. ~~Plural icons~~: removed 2026-09-29, **ruled by designer**
    ([ICON_LIBRARY.md](ICON_LIBRARY.md#removed-plural-icons), why):
    every view shows the effective icon as is; a task with subtasks
    shows its status icon, the folders stay as regular icons. One
    themed status icon, `TaskStatus.icon_id()`, replaces
    `getBitmap()`, which read the light theme's icons only.

## Deferred or Will Not Do

Moved out of the To Do list, **ruled by designer 2026-09-29**: pushed
beyond this refactor or not done, and not reported as outstanding.
Numbered D1, D2, ...

- D1. Renames too wide for this refactor, from the PEP 8 review of
  2026-09-29 ([PEP8_MIGRATION.md](PEP8_MIGRATION.md)): the domain and
  viewer methods the branch rewrote (`addChild`, `removeChild`,
  `computedStatus`, `processReminder`, the viewers' `onSelect`,
  `createWidget`, `_createColumns` and `subjectImageIndices`, the
  Publisher's `registerObserver` and `removeObserver`); keyword
  families: the date and time widgets' arguments (7 files),
  `taskList` and `effortList`, the export's `cssFilename` and
  `selectionOnly`.
- D2. The GTK warning at every launch
  (`gtk_distribute_natural_allocation: assertion 'extra_space >= 0'
  failed`), **ruled by designer 2026-09-29**: it comes from inside
  GTK at the main window's first show, with no Python code on the
  stack (traced under gdb with `G_DEBUG=fatal-criticals`); left in the
  logs as is.
- D3. Attachment styling, **ruled by designer 2026-09-29**: deferred,
  not in this release. Attachments keep drawing only their own style,
  as on master ([APPEARANCE_STYLES.md](APPEARANCE_STYLES.md#todo)).
- D4. One base class for the two tray icons, **ruled by designer
  2026-09-29**: will not be done; the classes are different by
  design ([SYSTEM_TRAY.md](SYSTEM_TRAY.md#code-duplication)).

## Pre-existing Issues

Optional, **requested by designer 2026-09-29**: problems present
before this refactor (on master, or failing in the baseline test run),
found along the way. Fixing them helps stabilize this work; none is
required. Numbered apart from the To Do list, crossed out when fixed.

Test files failing in the baseline run (28 tests before this
refactor; unchanged by its steps, crossed out when fixed):

- P1 to P4. ~~The integration tests (`SaveTest.py`, `LoadTest.py`,
  `ModelAndViewerTest.py`, `LeakTest.py`, `PerformanceTest.py`, 10
  errors)~~: fixed 2026-09-29. Their mock application had fallen
  behind: it now gets its settings before `init()` and its own
  translator, as the application does, and quitting skips idle
  processing when no event loop runs. The tests also remove the lock
  files they leave.
- P5. ~~`unittests/AppTest.py`: 2 failures (language from the
  locale)~~: fixed 2026-09-29, the tests only. The app reads `LANG`
  first, so the tests took the machine's language; they now set it.
- P6. ~~`unittests/commandTests/CutCopyPasteTest.py`: paste (1 error,
  1 failure)~~: fixed 2026-09-29, the tests only. A note cut by one
  test stayed on the shared clipboard for the next (every command
  test now clears it); the effort paste passed the task list as the
  destination, which the task viewer never does.
- P7. ~~`unittests/domainTests/EffortTest.py`: 4 failures (duration
  and revenue events on a start or stop change)~~: fixed 2026-09-29,
  the tests only. An effort's duration is stored and recalculated by
  the editor's entry mode
  ([DURATION_CALCULATIONS.md](DURATION_CALCULATIONS.md#edit-effort-window)),
  so a start or stop change sends the start or stop and the task's
  time spent; the effort viewer refreshes the row on them.
- P8. ~~`unittests/domainTests/TaskTest.py`: 3 failures (budget left
  events without a budget)~~: fixed 2026-09-29, the tests only. Since
  January 2026 (#334) budget left is the budget less the time spent
  with or without a budget ([TASK_FIELDS.md](TASK_FIELDS.md)); the
  tests expected 0 without one.
- P9. ~~`unittests/domainTests/SorterTest.py`: 2 failures (tree mode
  delegation)~~: fixed 2026-09-29, the tests only. Since master's
  March 2026 change a sorter passes its tree mode to its filter, as
  in the app; the tests' stand-in was a plain task list.
- P10. ~~`unittests/widgetTests/WindowDimensionsTrackerTest.py`: 2
  failures (size, move)~~: fixed by master's window geometry work,
  merged 2026-09-29.
- P11. ~~`unittests/guiTests/MainWindowTest.py`: 1 failure~~: fixed
  2026-09-29 with the merge, the test only: the maximize comes once
  the placement is quiet, and unloaded settings start minimized; it
  is skipped without a window manager to grant the maximize.
  ~~`thirdPartySoftwareTests/wxPythonTest.py`~~: fixed 2026-09-29,
  the test only: since wxWidgets 3.2, GTK also sends no text event
  when an empty text control is cleared.
  ~~`widgetTests/DragAndDropTest.py`~~: fixed 2026-09-29, the test
  only: its tree showed its root, which a tree selects by itself, so
  a drag took the root; the app's trees hide it.

In the app:

- P12. ~~Closing an editor after using a date popup logs a
  RuntimeError~~: fixed 2026-09-29, 3 times of 3 before, 0 of 4
  after. GTK sends one more text event while the control is
  destroyed; the handler exits when its control is gone.
- P13. ~~The calendar's month view fails under wxPython 4~~: fixed
  2026-09-29. With a calendar saved in month view the app did not
  start; `wx.DateTime.GetNumberOfDays()` replaces the removed call,
  with the date's year (the old calls used the current year's
  February), an unused one is dropped, and a header bound is appended
  as one tuple.
- P14. ~~A zero-size calendar pane assertion at startup~~: closed
  2026-09-29, **ruled by designer**: not reproduced in any run, a
  calendar in month view included.
- P15. ~~A list's tooltip stays shown over an editor opened from
  it~~: fixed 2026-09-29. It hid only when the mouse moved or left
  the list; opening an editor now hides it and drops a pending one.
- P16. ~~The GTK warning at every launch~~: not an issue, moved to
  [Deferred or Will Not Do](#deferred-or-will-not-do), D2.
- P17. ~~Invalid escape sequences in three test files~~: fixed
  2026-09-29, raw strings.
- P18. ~~The dependency graph viewer's size event method outside its
  class~~: fixed 2026-09-29 (not run: igraph is not installed here).
- P19. ~~`languagetests/TranslationIntegrityTest.py` fails to
  load~~: fixed 2026-09-29, the test only. It used the compile step
  the Python 3 migration retired; it now reads the `.po` files as the
  app does ([TRANSLATIONS.md](TRANSLATIONS.md)). All placeholders
  match.
- P20. ~~Belarusian, Danish, Hungarian and Swedish, 99 to 100%
  translated, were disabled~~: enabled 2026-09-29, **ruled by
  designer**; Danish's Preferences code corrected to `da_DK`. A
  string not translated shows in English.
- P21. ~~The language from the environment read `LANG` before
  `LC_ALL`~~: fixed 2026-09-29, **ruled by designer**: POSIX order,
  the first set of `LC_ALL`, `LC_MESSAGES` and `LANG`
  ([LOCALE.md](LOCALE.md)).
- P22. ~~In the task tree, Ctrl+Enter (Mark task completed) opened
  the selected task's editor, as Enter does~~: fixed 2026-09-29; the
  same on master. The tree edits on a plain Enter only.
- P23. ~~In the task editor, pasting several notes added only the
  first~~: fixed 2026-09-29; the same on master. The command paired
  one owner with the notes.
- P24. ~~Opening the open file again (a reload) released its lock
  between the close and the load~~: fixed 2026-09-29; the same on
  master ([FILE_LOCKING.md](FILE_LOCKING.md)).
- P25. ~~The notification centre's 1 s timer ran from its first
  notification on~~: fixed 2026-09-29; the same on master. It ticks
  only while it shows or holds notifications.
- P26. ~~A task file without the taskcoach version raised an
  UnboundLocalError~~: fixed 2026-09-29; the same on master. The
  reader refuses it with a clear error; the empty `PIParser` is gone.
- P27. ~~The tests loaded the icon catalog twice and logged each icon
  as an ID conflict~~: fixed 2026-09-29; the same on master.
- P28. ~~The editor's Check all and Uncheck all categories linked
  only the task's side~~: fixed 2026-09-29; the same on master. The
  file stores the category's side, so the categories were lost on
  save; they were not undoable either. Both now go through one
  command, both sides, like a single check.
- P29. Pasted notes lose their categories on save: a pasted task's
  notes, and a note pasted in the task editor. The same on master.
  Membership is held twice in memory (the item's categories, the
  category's members) and the file is written from the category's
  side, which paste does not fill for notes. Open: the fix is a design
  choice (the item's categories are its own data and the members
  derived, [ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)).
  The designer wants it solved at the source, no mix (2026-09-29).
  Today both sides are stored and written: both by the commands, the
  readers and merge; one alone by constructors (copies), undo of one
  object's state, and each list filling the other's side when items
  are added (the category list the items', the task list the
  categories', not for owned notes). 66 calls read the item's side,
  10 the category's (the writer, the category filter, merge). Options:
  A. store it on the item only, the members an index kept by the
  item's changes and by items entering or leaving the file, the file
  written from it (format unchanged); B. store it on the category
  only, the item's categories an index; C. both, with one writer.
  Recommended: A. Checked 2026-09-29: the ownership was decided on
  2026-09-28 (to do 17, commit 8b9d012a7: the task owns its category
  links; the category's list became the reverse and sets no date); the
  list stayed stored because the category list uses it when a category
  is deleted (the members lose it), undeleted (they get it back),
  copied or cut and pasted (the members join), and the file keeps the
  category's side so released versions read it. With A those
  operations carry the members themselves, as items carry their
  categories, and the file is written in the same format.

## Views on the Effective Styles

To do 35. **Decided before this refactor**
([TASK_STATUS.md](TASK_STATUS.md#legacy-code-compatibility-resolved)):
new code reads `effectiveXxx()`, and the legacy `recursive=True` style
accessors stay only until their consumers move; the migration waited
for the effective styles to prove stable. Only the editor had moved;
every view drew from the legacy accessors, cached by
`Task.recomputeAppearance()` outside the loop, while the loop computed
the effective styles every pass for nothing but the editor.

Done 2026-09-28: every view draws `shown_fg_color()`,
`shown_bg_color()`, `shown_font()` and `shown_icon_id()`
([APPEARANCE_STYLES.md](APPEARANCE_STYLES.md#what-the-views-draw)), and
the legacy code is gone.

The two rules differ, so moving changes what some rows look like:

- Several coloured categories: the legacy rule mixes their colours and
  fonts; the effective rule takes the highest style priority's (seen
  2026-09-28: purple drawn, red effective). **Ruling, 2026-09-29:**
  equal priorities (0 by default) take the first category by name, not
  a mix ([APPEARANCE_STYLES.md](APPEARANCE_STYLES.md#category-style-priority)).
- A subtask with no colour or category of its own: legacy takes its
  parent's category colours, else its status colour; effective takes
  its parent's own or category style, else its own status. **Ruling,
  2026-09-29:** the effective rule stays, for icons too: styles set on
  a parent carry down the hierarchy; whoever wants the status icons
  sets no icons or categories.
- Styles set by categories or the status appear at the loop's next
  tick (within a second); an item's own style at once, as before.

Found on the way, fixed:

- The effective rule gave a subtask its parent's status and tracking
  styles (a completed subtask of an active task drawn active, the
  clock on every subtask of a tracked task): a task's own state is no
  longer passed down, as the views always showed (to do 35.9).
- A task's status icon never reached its effective icon: the status
  getter's name was wrong since #386.
- The effective setters sent one event per value, default and source:
  up to three refreshes per style change, now one.
- Until the loop's first pass styles a new or loaded task, its icon is
  empty; the calendar drew it as an invalid bitmap and lost tasks, the
  start tracking menu logged an invalid icon. Both skip it now, as the
  trees, tooltips and tray already did.

Scan, 2026-09-28 (sources the loop does not compute: none left after):

| Where | Legacy use | Now |
|---|---|---|
| `widgets/treectrl.py`, `widgets/listctrl.py` | Row colours, font (every tree and list view) | `shown_fg_color()`, `shown_bg_color()`, `shown_font()` |
| `widgets/hcalendar.py`, `widgets/calendarwidget.py` | Task colours, font, icon | The same, `shown_icon_id()` |
| `gui/viewer/base.py` `subjectImageIndices()`, `gui/viewer/task.py` `get_icon_id()` | Subject icons | `shown_icon_id()`: the effective icon (the plural transform removed, to do 58) |
| `gui/viewer/task.py` Timeline, Square map | Colours, font | `shown_*()` |
| `gui/viewer/task.py` task graph | `task.foregroundColor(recursive=True)` (the wrong variable: `task`, not `tsk`) | `tsk.shown_fg_color()` |
| `gui/taskbaricon.py`, `gui/uicommand/uicommand.py` (start tracking menu) | Task icons | `shown_icon_id()` |
| `persistence/html/generator.py` | Export and print row colours | `shown_fg_color()`, `shown_bg_color()` |
| `gui/dialog/editor.py` owned-item lists | Notes, efforts, attachments rows | `shown_*()` |
| `domain/effort/base.py` | An effort's colours and font: its task's legacy ones | Its task's `shown_*()` |
| Old event `appearanceChangedEventType()` | Refreshes the task, category, note and effort views, the tray, editor pages, composite efforts; the task filter uses it for status changes | The effective-style events; the filter and the tray the status event; the event stays as an item's own style change |

---

## Master Design

The old master loop scanned every category, task and note every second
([Cost Before](#cost-before)). The goal is a cheap entry point each
second, and the full scan only at the seconds when time or data
changes something: instead of every second, only when a second
matters.

1. **One master timer list**: every second not processed yet at which
   something changes, in a binary heap (`heapq`). Seconds are only ever
   added, on every change; they leave only when processed. An entry
   may lie in the past: it is then simply due.
2. **Whole seconds, one rule**: every date and time is a whole second
   ([Time Resolution](#time-resolution)), and each entry is the first
   whole second at which its rule holds. A rule that holds after a
   date (overdue: due `<` now) gets the second after it; a rule that
   holds from a date on (active: actual start `<=` now) gets the
   date's own second. No other case.
3. **Each second**: if the smallest entry is at or before now, pop
   every entry up to now and run the full loop once, however many
   were due. Otherwise nothing else runs. A reminder set in the past,
   a file just opened, a late tick or a jump forward (suspend, resume)
   all come down to entries at or before now.
4. **The full loop**: run the full master loop, as today, with the
   statuses computed at the current second: every status, reminder and
   style, in one place. This is how the recursive updates stay
   manageable: subtasks, categories, prerequisites. **The cascade runs
   through the heap** (ruling below): one pass per second, never a
   loop inside a tick.
5. **Clock set back** (a time change): rebuild the heap from the tasks.
   The seconds between the new time and the old one are future again;
   the ones before it are due, so the full loop runs at once.
6. **Data changes**: a change to anything the full loop reads (an edit,
   a task added, a category's colour, an appearance setting) pushes
   the current second, so the loop at the next tick recomputes the
   styles and the cascades through the hierarchy
   ([Data Changes](#data-changes)).

## Time Resolution

**Ruling, 2026-09-27:** every date, time and duration Task Coach
stores, computes or compares is a whole second: task dates, reminders,
efforts, the scheduler's clock, the statuses computed from them, and
the task file. Only logs carry fractions of a second: their
timestamps stay high resolution, to show the flow in detail. Timer
delays in the UI (debounce, animation, the window geometry's quiet
periods) are not time values and are not concerned: they run in
milliseconds through `patterns.later`, apart from the master loop
([DEFERRED_CALLS.md](DEFERRED_CALLS.md)).

**Amended, 2026-09-27:** the creation and modification dates are
logging data, not functional data: they keep the logs' precision
(microseconds, `date.Timestamp`), in memory and in the file, so
changes within one second stay ordered when merging keeps the newest
copy ([ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#modification-date)).
A file written in whole seconds reads as whole seconds.

Why: the master timer list works in seconds, with one rule for every
entry. A fraction of a second would add cases (rounding up or down,
equal or not) and has no meaning for a user. One consequence: a task
planned to start "now" becomes late the second after, not a few
microseconds after.

How: `DateTime` and `TimeDelta` drop the microseconds whenever one is
made: the clock (`date.Now()`), parsing a file or an import,
arithmetic, `replace()`, `fromtimestamp()`, `fromDateTime()`. Every
value goes through them, so no path needs its own rounding. A file
written before keeps loading: its fractions are dropped on reading and
not written again.

**Ruling, 2026-09-27: the unset date is the infinite date.** A date
not set is the latest whole second, 9999-12-31 23:59:59 (canon, with
its reasons:
[ATTRIBUTE_PATTERN.md](ATTRIBUTE_PATTERN.md#dates-not-set-is-the-latest-date)).
For the master timer list, an unset date is simply the last possible
second of the schedule: the entries it gives sit at the very end of
the list and are in practice never reached, so the list needs no "is
it set?" case. The "second after" rule stops at the latest second, as
no later one exists.

Sweep, to leave nothing behind in this branch:

- [x] `DateTime` and `TimeDelta` constructors drop the microseconds;
  whole-second tests for every way of making one
  (`WholeSecondsTest`, `TimeDeltaTest`)
- [x] The unset date (`DateTime()`, `DateTime.max`) is 9999-12-31
  23:59:59; `endOfDay()` is 23:59:59
- [x] XML reader: end of day 23:59:59, start of day 00:00:00, no
  microsecond defaults
- [x] Recurrence, suggested dates and date helpers no longer copy or
  set microseconds
- [x] The date control's default "now" and the effort editor's "Stop
  now" are whole seconds (starting tracking and snoozing use
  `date.Now()`)
- [x] `TimeDelta.max` and `min` in whole seconds, as `DateTime.max`:
  "time left" of a task without a due date still shows as infinite
- [x] Tests no longer pass fractions, except those checking they are
  dropped
- Kept: `log_step()` and the other log timestamps; `perf_counter()`
  durations in traces; UI timer delays in milliseconds

## Index

- [To Do](#to-do)
- [Deferred or Will Not Do](#deferred-or-will-not-do)
- [Pre-existing Issues](#pre-existing-issues)
- [Views on the Effective Styles](#views-on-the-effective-styles)
- [Master Design](#master-design)
- [Time Resolution](#time-resolution)
- [The Master Timer List](#the-master-timer-list)
  - [Stale Entries](#stale-entries)
- [What Changes the Master Timer List](#what-changes-the-master-timer-list)
- [Data Changes](#data-changes)
- [Cost Before](#cost-before)
- [Cost After](#cost-after)
- [Incremental Pass](#incremental-pass)
- [ID Review](#id-review)
- [How It Was Measured](#how-it-was-measured)
- [History: One List on the Tick, Not a Timer per Event](#history-one-list-on-the-tick-not-a-timer-per-event)

---

## The Master Timer List

The entries, per task, each the first whole second at which its rule
holds:

| Rule | Holds when | Entry |
|---|---|---|
| Late | Planned start `<` now | The second after the planned start |
| Active | Actual start `<=` now | The actual start's second |
| Due soon | Due less the due soon hours `<` now | The second after it |
| Overdue | Due `<` now | The second after the due |
| Reminder | Reminder less 2 s `<=` now (2 s ahead, as today) | That second |

Dates are whole seconds ([Time Resolution](#time-resolution)). These
are the only time conditions in the loop: `Task.compute_status()`
(overdue, due soon, active, late, each on the task's own dates, not
its subtasks') and `processReminder()`.
Completion is not one: a completion date, even a future one, makes the
task completed at once. Styles read time only through the status.

Completed tasks get entries too: one rule for every task, and
completing or reopening one needs no signal. At an entry of a
completed task the full loop finds nothing new.

One function gives a task's entries; the build, the add event and the
field changes all use it.

The entries are seconds only, without their task: the full loop needs
no more. A date changed or a task deleted leaves its old second in the
heap; at that second the full loop runs, finds nothing new, and the
second is gone with the others popped. Removing it earlier would need
its task and the reason it was added (which rule, or which change to
cascade): the whole analysis over again
([Incremental Pass](#incremental-pass)). Entries leave the heap
only when popped, or when it is emptied or rebuilt. This leaves stale
entries that grow with the edits: open, to do 57
([Stale Entries](#stale-entries)).

The due entries are popped before the loop runs, not after: a second
pushed during the loop at or before now stays and runs the loop at the
next tick.

Every change pushes its seconds, duplicates included: identical
seconds are popped together and give one loop. Tasks added (a file
opened, a paste, an import) push their seconds one by one (25,000
into an empty heap: 4.7 ms); a rebuild
(the clock set back, the due soon hours changed) collects every task's
seconds and calls `heapify()` once.

Opening a file: `TaskFile.load()` empties the task list, then adds the
file's tasks in one add event. The heap is emptied with the task list
(its remove event leaving it empty), so the file's tasks fill an empty
heap; their past seconds are due, so the next tick runs the full loop
once and pops them.

The minute and day changes only tell viewers to refresh; they stay the
tick's own checks.

Size and cost, measured with `heapq` on `datetime`s: 5000 tasks give
25,000 entries after a rebuild, about 1.4 MB; edits add more
([Stale Entries](#stale-entries)). Building the heap takes 1.1 ms,
a push and a pop 0.4 us, the check each second (the smallest entry)
0.06 us. After the first loop only the future entries remain.

### Stale Entries

To do 57. **Open, reopened by designer 2026-09-29.**

Every task has five entries, one per rule; a date not set gives an
entry at the latest date (year 9999), never reached, so no "is it
set?" check is needed. A change to a task's dates pushes its five
seconds again, and those of each ancestor; the old ones stay, since
an entry without its task cannot be found to remove. So the heap grows
with the edits, not the tasks: stale future seconds stay until due,
and those at year 9999 never leave.

Stopgap, 2026-09-29: when the heap has doubled since its last rebuild
(plus 64), `_rebuild()` makes it again from every task's seconds. It
bounds the size but does not solve the cause, and adds costs:

- A full pass over every task (`timer_seconds()` of each), at a moment
  set by the edit count, not by a rule of the design.
- One full loop at the next tick: the rebuild pushes a second due at
  once, which also keeps a pending data change second it drops.
- A size threshold chosen by hand.

First thoughts, nothing decided:

1. **Entries carry their task and rule** (`(second, task, rule)`), as
   the incremental pass's step 1 would ([Incremental Pass](#incremental-pass)).
2. **Each task knows its current entries**, so a date change replaces
   exactly its own and a deleted task removes its own.
3. **A sorted list instead of a heap** (`bisect`), which allows removing
   an entry; or a heap whose popped entries are checked against their
   task's current ones and dropped when stale. The first removes at
   once; the second still keeps stale entries until due.
4. **No entry for a date not set**: the latest date is never reached,
   so nothing needs to wait for it.

With these, the list holds exactly the pending seconds, and no rebuild
is needed except for the clock set back and the due soon hours. Part
of the incremental pass's design ([Incremental Pass](#incremental-pass),
Design, 1).

---

## What Changes the Master Timer List

For time, the list listens to three signals, each pushing the
seconds of the tasks concerned (data changes push the current second
as well: [Data Changes](#data-changes)):

| Signal | Today | Change to the list |
|---|---|---|
| A task's due, planned start, actual start or reminder changed | Publisher `task.<field>` from the field's change callback, the task as source ([PUBLISHER_OBSERVER.md](PUBLISHER_OBSERVER.md#migration-log)) | Push the task's seconds |
| Tasks added to the task file's task list | Publisher add event of the task list; `extend()` includes every subtask | Push their seconds |
| Due soon hours changed | Publisher `behavior.duesoonhours`, the settings as source | Push every task's due soon second |

Each ancestor is a source of the same event too; it pushes the
ancestor's own seconds again, a harmless duplicate.

A second pushed at or before now is due at the next tick: a
reminder set to a past time fires, a task pasted with a past due date
is shown overdue.

Clock changes: a tick earlier than the one before rebuilds the heap
([Master Design](#master-design), 5). Jumping forward needs nothing:
the seconds passed are due.

### Why Nothing Is Missed

Checked in the code, 2026-09-27:

- **The three dates and the reminder** are private `Attribute`s. Their
  only writes are the constructor and `Attribute.set()`, which calls
  the change callback on every change; nothing reaches them another
  way (no `_Task__` access). The reminder was a plain field until step
  4, written in `set_reminder()` and both branches of
  `snooze_reminder()`.
- **The constructor** sends no change: the add event covers it. Every
  way a task enters the task file ends in `extend()` or `append()` on
  its task list: new task or subtask, paste, template, undo of a
  delete, file opened or merged, CSV and Todo.txt import. Commands given a
  viewer's list pass through to the task file's.
- **The due soon hours** are the only setting in the time conditions;
  the reminder's 2 s is a constant.

Which signal covers each action:

| Action | Signal |
|---|---|
| Date set, changed or cleared: editor, viewer, calendar or timeline drag, presets, planned duration, start tracking setting an empty actual start, effort commands, Mark active or inactive | Field changed |
| Recurring task completed: `recur()` reopens it and moves its dates and reminder | Field changed |
| Reminder set, changed, snoozed or cleared: editor, reminder dialog, completion of a non-recurring task | Field changed (reminder) |
| Undo or redo of an edit: `__setstate__()` calls the setters | Field changed |
| New task or subtask, paste, template, import, file opened, file merged, undo of a delete | Tasks added |
| Due soon hours, Preferences | Due soon hours changed |
| Delete, cut, undo of an add | None: the old seconds stay, find nothing and are removed when processed |
| Completed or reopened | None: completion is not a time condition, and completed tasks keep their entries |

No other change gives a task new time seconds: moving a task to
another parent, prerequisites (a task waiting for one keeps its
entries; the full loop finds it inactive), categories, subjects,
styles, other settings.

---

## Data Changes

**Rule:** a change to anything the full loop reads pushes the current
second. The loop at the next tick recomputes every status, style and
cascade through the hierarchy, as it does today every second. Several
changes in one second are popped together: one loop.

What the loop reads, so what pushes the current second:

- A task's dates, completion, reminder, recurrence, prerequisites,
  categories, parent, own colours, font and icon, efforts being
  tracked, notes and attachments
- A category's or a note's colours, font, icon, parent, and a
  category's style priority
- Tasks, categories, notes and attachments added or removed
- The appearance settings (colour, font and icon per status, light and
  dark), the theme, the due soon hours

The hook is the domain's modification events (`_data_event_types()`
in `gui/scheduler.py`), a task's tracking, and the loop's own outputs
(status, derived and effective styles), except fields that change no
status, reminder or style, such as the subject, the description, the
fees, the priority and the expanded state, so typing does not run the
loop every second. A name the loop reads only as the style source it
gives other items ("[Category] Work"): renaming a category, or an item
with children, pushes the second; a leaf's name runs nothing. Computed values the loop does not read (time
spent, budget left, revenue, the subtree values) run nothing.

The safe side decides doubtful fields: one wrongly left in costs a
loop; one wrongly left out is a miss, which the check mode of item 5
logs. Settings are the other way round: only the sections listed
above, as window and other settings change often and the loop reads
none of them.

### Ruling: the Cascade Runs Through the Heap

**Ruling, 2026-09-27 (design intent).** When the heap has a due entry,
the full loop runs once over all objects. Every change it makes (a
status, a style, a reminder cleared) is a change like any other: it
pushes the current second, or the task's new seconds, into the heap.
The next second, the heap is due again and the loop runs again. So the
cascade through the hierarchy needs no logic of its own: it settles
one pass per second, like today's loop, but only while something still
changes.

- **No freeze**: one pass per tick at most, never a loop inside a
  tick; the UI runs between passes.
- **No pass for nothing**: a pass that changes nothing pushes nothing,
  so the next second runs nothing. Unchanged values send no event
  (item 3), and a reminder trigger is not a change: triggered again
  while its dialog is open, it is dropped
  ([Reminders](#data-changes)).
- **It settles**: styles flow one way (category to task, parent to
  child) and statuses come from the saved data, so no change feeds
  back into its cause. Today's loop settled after a file opened in
  two passes: the third changed nothing (the prototype's trace,
  2026-09-27, 200 tasks).
- **Fewer passes**: the loop visits parents first (`allItemsSorted()`;
  today it visits tasks and categories in set order, so a child seen
  before its parent took the parent's old style), so most cascades
  settle in the first pass and the second only finds nothing.

The only dates a pass writes are reminders: a completed task's
reminder cleared by `processReminder()`. Its change pushes the task's
seconds (the unset date's, at the end of the heap) and the current
second, like any other change.

**Reminders** follow the design: the full loop at the reminder's second
triggers it once. The trigger every second while a reminder is due goes
away: the controller drops a trigger only while the task's dialog is
open, and no dialog action leaves a reminder due (closing snoozes or
clears it, marking completed clears or advances it, a deleted task
closes it).

---

## Cost Before

Time of one tick, measured 2026-09-27 in the real app on the desktop
(Debian 13, wxPython 4.2.3), with the `[SCHEDULER]` trace line of the
prototype (median and maximum of 60 ticks, idle, first minute after
loading left out) and files from `tools/generate_task_file.py`
(parents with 9 subtasks, 20 categories, 50 notes, dates 20 days and
reminders 2 days around now):

| Tasks | Today | Without events for unchanged values |
|-------|-------|-------------------------------------|
| 200 | 39 ms, max 70 | 30 ms, max 57 |
| 2000 | 258 ms, max 439 | 197 ms, max 280 |
| 5000 | 620 to 670 ms, max 1000 | 472 ms, max 575 |

It runs on the UI thread every second: with 2000 tasks the UI is
blocked a quarter of the time, with 5000 two thirds, so typing,
scrolling and window resizing stutter.

The first full loop after a file is opened is slower (15 s with 2000
tasks, 57 s with 5000); the refactor runs it the same way, so it is
not part of this plan.

The earlier profile (a scratch copy under Xvfb, 2000 tasks):
`computeStyles` 69%, `compute_stored_status` 17%,
`recomputeLegacyStatus` 8%. Nearly all of it recomputes unchanged
values; `Attribute.set()` created and sent an empty `Event` for each of
about 40,000 unchanged values per tick (the second column removes
that).

---

## Cost After

Measured 2026-09-27 in the real app on the desktop with the
`[SCHEDULER]` minute line ([SCHEDULERS.md](SCHEDULERS.md#masterscheduler-processing-flow)):

| File | Before | After |
|---|---|---|
| 2000 tasks, dates 20 days around now, idle | 258 ms every second | 1 pass a minute, 213 ms; 59 of 60 ticks do nothing |
| 200 tasks, dates 60 minutes around now | 39 ms every second | 2 to 4 passes a minute, about 50 ms each |
| 2000 tasks, dates 60 minutes around now (about 25 statuses changing a minute) | UI thread busy 98%, 5 to 10 ticks a minute, autosave re-reading the file after every status change | Busy 11%, the passes; 28 to 54 ticks a minute ([To Do](#to-do), 11) |

Nothing missed: with `TASKCOACH_SCHEDULER_CHECK=1` the full loop ran
every second as well for 3 minutes with 200 tasks and with 2000, dates
within 60 minutes (about 25 statuses changing a minute), and made no
change at a second the heap did not call for.

Each due second costs its pass and one more that finds nothing (the
[cascade ruling](#ruling-the-cascade-runs-through-the-heap)).

---

## Incremental Pass

To do 45, with to do 57 ([Stale Entries](#stale-entries)). **Analysis
2026-09-29, verified; nothing built or decided.**

The designer's idea (2026-09-29): a master list of the seconds, each
with its tasks; when a second lands, process its tasks and cascade
only what they change, each object once, instead of the full loop over
every object; data changes (a category's icon or priority, a move)
cascade the same way, through the Publisher events.

**Verdict: it can match the full loop exactly.** Checked by a
differential probe: after each of 300 to 400 random changes (16 kinds:
overrides, category links, priority, renames, moving tasks and
categories, tracking, dates, completion, prerequisites, new and pasted
tasks with owned notes, subnotes, delete and undelete,
`__setstate__`, clock jumps of 1 s to 30 h), on 7 files of 167 to 714
objects, an emulated incremental pass ran, then the real full loop:
0 values left for the full loop, 0 objects out of order, 0 processed
twice; 6 to 13 objects per change. Dropping any rule below brings
misses back. The one difference in principle: the full loop triggers
a due reminder again at every pass, the incremental pass at its second
only; no action in the interface leaves a reminder due after its
dialog closes.

### Design

1. **The timer list** (to do 57): a sorted list of `(second, task,
   rule)`; each task knows its entries, so a date change replaces them
   and a deletion removes them; no entry for a date not set. A landing
   second gives its tasks: their status and reminder are computed, and
   a changed status marks the task's style.
2. **Marks from events:** each change the scheduler already hears
   ([Data Changes](#data-changes)) marks the objects that read it
   (Followers below), by identity, not ID.
3. **Settling:** the marked objects in a fixed order: categories by
   depth, then tasks by depth, then notes (global and owned) by depth,
   then attachments. A changed effective value or source marks its
   followers, which always come later in the order, so each object is
   computed once and nothing loops.
4. **Global changes keep the full loop:** a file opened, a merge
   (copies share IDs), the clock set back, the due soon hours, the
   status styles (light and dark), the theme and the system colours.
5. **Proof, kept:** the differential probe becomes a unit test that
   compares against the full loop; the check mode
   (`TASKCOACH_SCHEDULER_CHECK=1`) stays for the app. No periodic full
   loop (ruling below).

Rules the first sketch lacked, each needed by the probe:

- Follow the `effective.*` events wherever they are sent: an override
  setter and `__setstate__` compute an object's effective style at
  once, outside the pass.
- A category's members are the items whose `categories()` hold it (an
  index), not `Category.categorizables()`: pasted items' owned notes
  keep their categories without the category's side.
- An added object is computed with its whole subtree (children, owned
  notes and attachments): each reads what is above it, its parent and
  its categories, so it inherits their styles; the fixed order settles
  what is above first.
- A category's rename or style priority change reaches its members:
  equal priorities are ordered by name.
- An owner's style reaches none of its notes or attachments.

### Verification

`docs/scripts/scheduler_diffprobe.py` (arguments: seed, steps, member
lookup, outside events; run it from the repository root with
`PYTHONPATH=.` under `xvfb-run`): 16 kinds of random change; after each,
an emulated incremental pass, then the real full loop. With the rules:
0 misses on seeds 1 to 7 (300 to 400 steps, 167 to 714 objects), 0
out of order, 0 twice, 5 to 13 objects per change. Dropping a rule:
members from `Category.categorizables()` gives 7 to 10 misses per 300
steps (seeds 1, 2, 4 to 7); not following effective events sent
outside the pass, 3 in 200 (seed 3). The full loop re-triggered due
reminders at nearly every step, the difference in principle above.
The first full loop after the random file is built changes about 705
values, the second none: the loop already settles in one pass.

`docs/scripts/scheduler_claims_probe.py` checks single claims: a
leaf category's rename with a member linked one way pushes nothing;
fonts from one string compare equal; an owned note and attachment
ignore their owner's style; default icons; an override changes the
effective style at once while the children wait for the pass.
`docs/scripts/category_membership_probe.py` reproduces P28 and P29.

### Inputs

| Result | Reads |
|---|---|
| Category style | own override; the parent category's effective value and name |
| Task style | own override; tracking (icon); its categories: their priority, name, ID and effective values; the parent task's effective value, source and name; its status and the status styles in the settings (light or dark theme) |
| Note style | own override; its categories (as a task's); the parent note's effective value and name; not its owner |
| Attachment style | own override only |
| Task status | own planned start, actual start, due and completion; the completion of the prerequisites of the task and its ancestors; the due soon hours; the clock |
| Task reminder | reminder (with snooze), completion, recurrence, the clock |

### Followers

| When this changes | Recompute |
|---|---|
| A category's effective value | its subcategories; its direct members (tasks, global and owned notes) |
| A category's name | its subcategories and direct members (source, and the winner of a tie) |
| A category's style priority | its direct members |
| A task's effective value or source | its subtasks (not when both old and new come from its own status or tracking) |
| A task's or note's name | its subtasks or subnotes (source) |
| A task's status | its own style; the filter and sorter (`scheduler.pass`) |
| A task's tracking | its own icon |
| A note's effective value | its subnotes |
| An owner's style, an attachment | nothing |

The graph has no cycles: edges run category to subcategory, category
to member, task to subtask, note to subnote, status to own style.
Prerequisites act through completion dates, at once, outside the pass
(`_update_status()`).

### Risks

- An owned note or attachment does not know its owner: deciding
  whether a marked one is still in the file needs an owner map or a
  walk from the file's items.
- Members come from the items' categories, which paste leaves
  one-sided for notes (P29); the member lookup depends on how P29 is
  solved at the source.
- Merge: copies share IDs; a full loop.
- The theme can turn dark or light for up to 1 s without its event;
  the full loop follows `system.theme_colour_changed` too.
- A failing object must still mark its followers.
- Over-marking costs work, not correctness: ancestors on date and
  tracking events, descendants on names.

Heard by the scheduler but read by no result, so the pass ignores
them: budget, percentage complete, planned duration and its mode,
dependencies, the mark completed setting, an attachment's location, a
category's filter and exclusive subcategories, an effort's start and
entry mode, ordering, the derived styles' events.

Questions for the review:

1. The cascade ruling ([Ruling](#ruling-the-cascade-runs-through-the-heap))
   spreads a cascade one level per second, so a pass never runs long.
   With each object computed once in a fixed order, settle it all at
   once instead? That also drops the empty pass each due second costs
   today.
2. ~~Keep a full loop as a safety net (once a minute, say), or only
   the check mode during development?~~ **Ruled by designer
   2026-09-29:** no periodic full loop; it would admit the pass cannot
   cover everything. A missed follower is found (the check mode) and
   fixed.
3. Worth it? Today the pass runs once a minute with typical files and
   costs 213 ms with 2000 tasks; the gain is large with big files and
   many dates close to now (2000 tasks, dates within an hour: UI
   thread 11% busy).
4. A due reminder triggered at its second only, not again at every
   pass?
5. When to settle: at the next tick, as today (within a second), or
   right after the change, all changes of one event dispatch together?
6. Category membership held twice (P29): store it on one side, or keep
   both with one writer? Decides the member lookup above.

---

## ID Review

Checked 2026-09-28, across the repository:

- Every task, category, note, attachment and effort gets an ID when
  created (`base.new_id()`, a random UUID), keeps it for life and saves
  it. Only reading a file and undo (each object's own state) set an
  existing ID.
- Copies get new IDs (`__getcopystate__()` leaves the ID and the
  creation date out): copy and paste, paste as subitem, the subtasks,
  notes, attachments and efforts copied with them, a task saved as a
  template and each task made from one. The first paste after a cut
  is a move: the cut items themselves, IDs kept.
- Creation and modification dates are the clock's time with
  microseconds; different items may share one.
- The same ID in two files is the same item: Save As, Save selection,
  backups; File > Merge matches items by it; Todo.txt `tcid:` updates
  the task it names (an unknown one is skipped, never created).
- A recurring task advances in place; no new task.
- Not item IDs: wx window and menu IDs (`IdProvider`), returned when
  a window closes.

---

## How It Was Measured

`tools/generate_task_file.py TASKS FILE [MINUTES]` writes the task
files; with MINUTES every date falls within that many minutes of now,
so statuses change and reminders fire while the file is open. The app
runs from the repository on the desktop with its own `--ini` settings,
`XDG_CONFIG_HOME`/`XDG_DATA_HOME` and a copy of the file, closed after
a few minutes; the `[SCHEDULER]` trace line gives the tick cost once a
minute. Each variant runs from its own `git worktree`, so edits made
meanwhile cannot leak into a run. The earlier numbers came from a
scratch copy of the app under Xvfb.

---

## History: One List on the Tick, Not a Timer per Event

A timer per event is the same idea, and it was tried: the scheduler
removed in January 2026 kept a sorted job list with one `wx.CallLater`
for the next job (see [SCHEDULERS.md](SCHEDULERS.md#historical-context)). The
list on the tick avoids its failures:

- The list holds seconds, not bound methods, so no unschedule can
  miss.
- A task's entries are taken from its fields whenever they change,
  never adjusted in each setter. The old setters missed cases: tasks
  loaded from a file bypass the setters ([DATETIME_PRESETS.md](DATETIME_PRESETS.md#reminder-scheduling-on-load)).
- No timer of its own, so nothing fires while dialogs are created or
  destroyed, and no timer outlives its owner
  ([CRASH_GUARD.md](CRASH_GUARD.md)).
- Comparing wall-clock time each tick handles suspend and clock
  changes; a relative timer fires at the wrong wall time.
- The list can be logged.

**Tried and dropped, 2026-09-27:** one dirty flag running the full loop
only after a change. It listened to every event, and a due reminder's
trigger every second counted as a change, so the loop never skipped.
The cascade ruling keeps the idea without that fault: only the change
events push, and a trigger is not one. An uncommitted
prototype also went further than this design (entries carrying their
task, processed per object); what stays useful from it: the
`Attribute.set()` change, the once-a-minute `[SCHEDULER]` cost line,
and debug switches to profile the first ticks and to check a skipped
tick against the full loop.
